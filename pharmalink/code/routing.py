"""Module for bootstrapping the valhalla routing engine for use in the pharmalink project."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pharmalink.code.valhalla.lib.src.bindings.python.valhalla as valhalla


import importlib.resources as res
import shutil
import subprocess
import pathlib as path
import json
import os
import requests as req
import sys


lib_dir = res.files(__package__).joinpath("valhalla", "lib")
data_dir = res.files(__package__).joinpath("valhalla", "data")


def create_routing_actor(forced: bool = False) -> valhalla.Actor:
    """Create a new Valhalla routing actor.

    WARNING: Running this for the first time will trigger multiple lengthy build processes to bootstrap everything.

    Args:
        forced: Whether to build anew or lazy-load existing parts from cache.

    Returns:
        A valhalla.Actor instance.
    """

    if not lib_dir.exists() or forced:
        build_valhalla(forced=forced)

    if not data_dir.exists() or forced:
        build_graph(forced=forced)

    # Load the Valhalla library
    bindings_path = res.files(__package__).joinpath(
        "valhalla", "lib", "src", "bindings", "python"
    )
    sys.path.append(bindings_path.as_posix())
    import valhalla

    # Load the Valhalla configuration file
    config_file = data_dir.joinpath("valhalla.json")

    # Create a new Valhalla actor
    return valhalla.Actor(str(config_file))


def build_valhalla(forced: bool = False) -> None:
    """Build the Valhalla routing engine.

    Please note that this will only work on macos in its current state.
    If needed, the build process should work on most Linux distributions by adjusting the package manager commands.
    The build process is loosely based on the official Valhalla documentation, but I had to adjust some of the steps, YMMV.
    """

    # Ensure the build subdirectory exists and is empty
    build_dir = res.files(__package__).joinpath("valhalla", "build")

    if lib_dir.exists() and not forced:
        print("Valhalla libraries found. Skipping build.")
        return

    # Continue with build if the Valhalla library is missing or forced
    print("Valhalla library not found. Building now...")

    # Remove existing Valhalla libraries and build directories
    if lib_dir.exists():
        shutil.rmtree(lib_dir)

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.mkdir(exist_ok=True, parents=True)

    # small wrapper around subprocess.run to improve code readability
    def subprocess_run(command, **kwargs):
        return subprocess.run(
            command,
            check=True,
            cwd=str(build_dir),
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
            **kwargs,
        )

    # Update PATH to include required binary locations
    os.environ["PATH"] = (
        "/usr/local/opt/binutils/bin:/usr/local/opt/coreutils/libexec/gnubin:"
        + os.environ["PATH"]
    )

    # These are the system dependencies required to build Valhalla
    # The very popular `Homebrew` package manager is used to install these dependencies
    # More information about Homebrew can be found at https://brew.sh/
    subprocess_run(
        [
            "brew",
            "install",
            "automake",
            "cmake",
            "libtool",
            "protobuf-c",
            "libspatialite",
            "pkg-config",
            "sqlite3",
            "jq",
            "curl",
            "wget",
            "czmq",
            "lz4",
            "spatialite-tools",
            "unzip",
            "luajit",
            "boost",
            "bash",
            "coreutils",
            "binutils",
        ]
    )

    # Clone the Valhalla repository from GitHub into the build directory
    subprocess_run(
        [
            "git",
            "clone",
            "--recurse-submodules",
            "https://github.com/valhalla/valhalla",
            str(build_dir),
        ]
    )

    # Configure cmake build
    subprocess_run(
        [
            "cmake",
            "-B",
            "build",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DENABLE_SERVICES=OFF",
            "-DENABLE_GDAL=OFF",
        ]
    )

    # Build Valhalla using all available CPU cores
    subprocess_run(["cmake", "--build", "build", "--", "-j", f"{os.cpu_count()}"])

    # Copy the built Valhalla libraries to the lib directory
    shutil.copytree(build_dir.joinpath("build"), lib_dir)

    # Remove the build directory
    shutil.rmtree(build_dir)


def build_graph(forced: bool = False) -> None:
    """Build the Valhalla routing graph for a given OSM input file.

    WARNING: This process is quite resource-intensive and can take a long time to complete.
    Unlike the library build, this should work on all systems out of the box.
    It is again loosely based on the official Valhalla documentation, but I had to hand-stitch the components together.
    """

    # TODO: Simplify the cache/data structure (optimally alike the OSM input file), it's a bit convoluted right now and duplicate copies should be unnecessary

    cache_dir = res.files(__package__).joinpath("valhalla", "cache")

    if data_dir.exists() and not forced:
        print("Valhalla graph found. Skipping build.")
        return

    # Continue with build if the Valhalla graph is missing or forced
    print("Valhalla graph not found. Building now...")

    # Cleanup existing Valhalla data directory
    if data_dir.exists():
        shutil.rmtree(data_dir)

    data_dir.mkdir(exist_ok=True, parents=True)

    # CONFIG FILE

    config_source = cache_dir.joinpath("valhalla.json")
    config_target = data_dir.joinpath("valhalla.json")

    print("Creating config file...")

    # Create the default config content
    default_config_builder = str(lib_dir.joinpath("valhalla_build_config"))
    default_config_run = subprocess.run(
        [default_config_builder],
        check=True,
        cwd=str(lib_dir),
        stdout=subprocess.PIPE,
    )
    default_config = json.loads(default_config_run.stdout)

    # Update the config with the paths to the input and output files
    custom_config_params = {
        "mjolnir": {
            "tile_dir": str(data_dir.joinpath("tiles")),
            "tile_extract": str(data_dir.joinpath("tiles.tar")),
            "admin": str(data_dir.joinpath("admin.sqlite")),
            "timezone": str(data_dir.joinpath("tz_world.sqlite")),
            "transit_dir": str(data_dir.joinpath("transit")),
            "transit_feeds_dir": str(data_dir.joinpath("transit_feeds")),
            "default_speeds_config": str(data_dir.joinpath("default_speeds.json")),
        },
        "additional_data": {
            "elevation": str(data_dir.joinpath("elevation_data")),
        },
    }
    # Merge the default and custom config
    config = default_config | custom_config_params

    # Write the final config to a file
    with open(config_target, "w") as file:
        json.dump(config, file)

    # Copy the built config file to the source directory for simple caching
    shutil.copy(config_target, config_source)
    print("Config file created.")

    config_file = config_target

    # ENSURE NECESSARY FILES EXIST

    # OSM INPUT FILE
    input_file = cache_dir.joinpath("germany.osm.pbf")

    if not input_file.exists() or forced:
        print("Downloading OSM input file...")
        input_url = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"

        # This file is around 4 GB in size, so we stream it to disk
        with req.get(input_url, stream=True) as request:
            request.raise_for_status()
            with open(input_file, "wb") as file:
                for chunk in request.iter_content(chunk_size=8192):
                    file.write(chunk)

        print("OSM input file downloaded.")

    # Default speeds file to enhance graph
    default_speeds_source = cache_dir.joinpath("default_speeds.json")
    default_speeds_target = path.Path(config["mjolnir"]["default_speeds_config"])

    # Download default speeds data
    if not default_speeds_source.exists() or forced:
        print("Downloading default speeds file...")
        default_speeds_url = "https://raw.githubusercontent.com/OpenStreetMapSpeeds/schema/master/default_speeds.json"

        with open(default_speeds_source, "wb") as f:
            f.write(req.get(default_speeds_url).content)

    shutil.copy(default_speeds_source, default_speeds_target)
    print("Default speeds file copied.")

    # Download transit data for Germany
    # transit_feeds_source = cache_dir.joinpath("transit_feeds")
    # transit_feeds_target = path.Path(config["mjolnir"]["transit_feeds_dir"])

    # if not transit_feeds_source.exists() or forced:
    #     # Create transit feeds directory and a subdirectory for Germany
    #     transit_feeds_source.mkdir(parents=True, exist_ok=True)

    #     # Download feed for Germany
    #     germany_dir = transit_feeds_source.joinpath("germany")
    #     germany_dir.mkdir(parents=True, exist_ok=True)

    #     # Download GTFS data for Germany
    #     gtfs_url = "https://download.gtfs.de/germany/free/latest.zip"
    #     # gtfs_url = ""

    #     print("Downloading GTFS data for Germany...")
    #     gtfs_file = germany_dir.joinpath("gtfs.zip")
    #     with open(gtfs_file, "wb") as f:
    #         f.write(req.get(gtfs_url).content)

    #     # Unzip the GTFS data
    #     with zipfile.ZipFile(gtfs_file, "r") as zip_ref:
    #         zip_ref.extractall(germany_dir)
    #     gtfs_file.unlink()

    #     print("GTFS data for Germany downloaded.")

    # shutil.copytree(transit_feeds_source, transit_feeds_target)
    # print("Transit data copied.")

    # BUILD ADMINS
    admins_source = cache_dir.joinpath("admin.sqlite")
    admins_target = path.Path(config["mjolnir"]["admin"])

    if not admins_source.exists() or forced:
        print("Building admins database...")
        admins_command = [
            str(lib_dir.joinpath("valhalla_build_admins")),
            "--config",
            str(config_file),
            str(input_file),
        ]
        subprocess.run(admins_command, check=True, cwd=str(lib_dir))

        # Copy the built admins database to the source directory for simple caching
        shutil.copy(admins_target, admins_source)

        print("Admins database built.")

    shutil.copy(admins_source, admins_target)
    print("Admins database copied.")

    # BUILD TIMEZONES
    timezones_source = cache_dir.joinpath("tz_world.sqlite")
    timezones_target = path.Path(config["mjolnir"]["timezone"])

    if not timezones_source.exists() or forced:
        print("Building timezones database...")
        timezones = subprocess.run(
            str(lib_dir.joinpath("valhalla_build_timezones")),
            check=True,
            cwd=str(lib_dir),
            stdout=subprocess.PIPE,
        )

        with open(config["mjolnir"]["timezone"], "wb") as f:
            f.write(timezones.stdout)

        # Copy the built timezones database to the source directory for simple caching
        shutil.copy(timezones_target, timezones_source)

        print("Timezones database built.")

    shutil.copy(timezones_source, timezones_target)
    print("Timezones database copied.")

    # TRANSIT DATA
    # transit_dir_source = cache_dir.joinpath("transit")
    # transit_dir_target = path.Path(config["mjolnir"]["transit_dir"])

    # if not transit_dir_source.exists() or forced:
    #     print("Building transit data...")
    #     ingest_transit_cmd = [
    #         str(lib_dir.joinpath("valhalla_ingest_transit")),
    #         "--config",
    #         str(config_file),
    #         str(input_file),
    #     ]
    #     subprocess.run(
    #         ingest_transit_cmd,
    #         check=True,
    #         cwd=str(lib_dir),
    #     )

    #     # Copy the built transit data to the source directory for simple caching
    #     shutil.copytree(transit_dir_target, transit_dir_source)
    #     print("Transit data built.")

    # shutil.copytree(transit_dir_source, transit_dir_target)
    # print("Transit data copied.")

    # TODO: Give this another go if possible. Parsing the transit data took over 10 days on a M1 Pro during a trial run (before failing due to a mistake on my part).
    # However, while transit is relevant for accurately representing used modes of transport, valhalla matrices can only be calculated for auto, pedestrian, and bicycle modes, anyways.

    # FIRST TILE BUILD
    tiles_source = cache_dir.joinpath("tiles")
    tiles_target = path.Path(config["mjolnir"]["tile_dir"])

    if not tiles_source.exists() or forced:
        print("Building first tiles...")
        tiles_command = [
            str(lib_dir.joinpath("valhalla_build_tiles")),
            "-e",
            "build",  # end at build stage, before enhance
            "--config",
            str(config_file),
            str(input_file),
        ]
        subprocess.run(tiles_command, check=True, cwd=str(lib_dir))

        print("First tiles built.")

        # ELEVATION TILES
        elevation_source = cache_dir.joinpath("elevation_data")
        elevation_target = path.Path(config["additional_data"]["elevation"])

        if not elevation_source.exists() or forced:
            print("Building elevation tiles...")
            elevation_command = [
                str(lib_dir.joinpath("valhalla_build_elevation")),
                "-v",
                "--from-tiles",
                "-z",
                "--config",
                str(config_file),
            ]
            subprocess.run(elevation_command, check=True, cwd=str(lib_dir))

            # Copy the built elevation tiles to the source directory for simple caching
            shutil.copytree(elevation_target, elevation_source)
            print("Elevation tiles built.")
        else:
            shutil.copytree(elevation_source, elevation_target)
            print("Elevation tiles copied.")

        # ENHANCE TILES
        print("Enhancing tiles...")
        enhance_command = [
            str(lib_dir.joinpath("valhalla_build_tiles")),
            "-s",
            "enhance",  # start at enhance stage, after build
            "--config",
            str(config_file),
            str(input_file),
        ]
        subprocess.run(enhance_command, check=True, cwd=str(lib_dir))
        print("Tiles enhanced.")

        shutil.copytree(tiles_target, tiles_source)
        print("Enhanced tiles copied to source.")

    else:
        shutil.copytree(tiles_source, tiles_target)
        print("Tiles copied.")

    # EXTRACT AND COMPRESS GRAPH

    extract_source = cache_dir.joinpath("tiles.tar")
    extract_target = path.Path(config["mjolnir"]["tile_extract"])

    if not extract_source.exists() or forced:
        print("Extracting graph...")
        extract_command = [
            str(lib_dir.joinpath("valhalla_build_extract")),
            "-v",
            "--config",
            str(config_file),
            "-O",
        ]
        subprocess.run(extract_command, check=True, cwd=str(lib_dir))

        # Copy the compressed graph to the cache directory
        shutil.copy(extract_target, extract_source)

        print("Graph extracted and compressed.")

    shutil.copy(extract_source, extract_target)
    print("Compressed graph copied.")

    print("Valhalla graph built. Ready to route.")
    return
