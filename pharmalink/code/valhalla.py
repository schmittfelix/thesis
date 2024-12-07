"""Module for the Valhalla routing engine."""

from __future__ import annotations
import importlib.resources as res
from tqdm.auto import tqdm
import shutil
import subprocess
import os
import json


def build_valhalla(force: bool = False) -> None:

    # Ensure the build subdirectory in the cache directory exists and is empty
    lib_dir = res.files(__package__).joinpath("valhalla", "lib")
    build_dir = res.files(__package__).joinpath("valhalla", "build")

    if lib_dir.exists() and not force:
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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

    # Copy the built Valhalla libraries to the cache directory
    shutil.copytree(build_dir.joinpath("build"), lib_dir)

    # Remove the build directory
    shutil.rmtree(build_dir)


def build_graph(force: bool = False) -> None:

    lib_dir = res.files(__package__).joinpath("valhalla", "lib")

    # Ensure the data directory exists and is empty
    data_dir = res.files(__package__).joinpath("valhalla", "data")

    if data_dir.exists() and not force:
        print("Valhalla graph found. Skipping build.")
        return

    # Continue with build if the Valhalla graph is missing or forced
    print("Valhalla graph not found. Building now...")

    # Remove existing Valhalla libraries and build directories
    if data_dir.exists():
        shutil.rmtree(data_dir)

    data_dir.mkdir(exist_ok=True, parents=True)

    input_file = res.files(__package__).joinpath("sources", "germany.osm.pbf")
    # input_file = res.files(__package__).joinpath("sources", "andorra-latest.osm.pbf")

    # CONFIG FILE

    # Create the default config content
    default_config_builder = str(lib_dir.joinpath("valhalla_build_config"))
    default_config_run = subprocess.run(
        [default_config_builder], check=True, cwd=str(lib_dir), stdout=subprocess.PIPE
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
    default_config.update(custom_config_params)

    # Write the final config to a file
    config_file = data_dir.joinpath("valhalla.json")

    with open(config_file, "w") as file:
        json.dump(default_config, file)

    return

    def run_valhalla_binary(binary, *args):
        print(f"Running {binary}...")

        # call the binary plus specific arguments and the config file
        command = (
            [str(lib_dir.joinpath(binary))]
            + list(args)
            + ["--config", str(config_file)]
        )

        # some binaries need to be called with the input file
        if not binary.endswith(("elevation", "transit")):
            command += [str(input_file)]

        subprocess.run(
            command,
            check=True,
            cwd=str(lib_dir),
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )

        # ingest traffic, then convert traffic
