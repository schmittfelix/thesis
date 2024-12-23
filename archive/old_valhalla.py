import docker
import importlib.resources as res
import tqdm
import shutil
import pathlib as path
import time
import requests as req


class ValhallaInstance:
    """An instance of the Valhalla routing engine running in a Docker container."""

    def __init__(self) -> None:

        # Connect to Docker daemon and catch the most common exception which is caused by the Docker daemon not running
        try:
            docker_client = docker.from_env()
        except docker.errors.DockerException:
            raise Exception(
                "Could not connect to Docker daemon. Please ensure Docker is running."
            )

        # Pull latest Valhalla Docker image
        docker_client.images.pull(
            "ghcr.io/gis-ops/docker-valhalla/valhalla", tag="latest"
        )

        # Check if matching valhalla tile data already exists
        valhalla_data = res.files(__package__).joinpath("cache", "valhalla")

        if not valhalla_data.exists():
            self._build_valhalla_tiles(docker_client, valhalla_data)

        # Create Valhalla service
        self.valhalla = self._create_valhalla_service(docker_client, valhalla_data)

    def _build_valhalla_tiles(
        self, docker_client: docker.DockerClient, data_path: path.Path
    ):

        # Ensure empty cache subdirectory "valhalla" exists and contains a copy of the OSM planet-extract for Germany
        data_path.mkdir(exist_ok=True, parents=True)

        # Ensure the main sources directory contains the planet-extract file
        raw_file = data_path.parent.parent.joinpath("sources", "germany.osm.pbf")

        if not raw_file.exists():
            print(
                "OSM base file for Valhalla Graph generation is missing. Downloading now (~ 4GB)..."
            )

            extract_url = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"

            request = req.get(extract_url, stream=True)
            request.raise_for_status()

            file_size = int(request.headers.get("content-length", 0))

            with tqdm.wrapattr(
                open(raw_file, "wb"),
                "write",
                miniters=1,
                total=file_size,
                desc=f"Downloading {raw_file.name}",
            ) as file:
                for chunk in request.iter_content(chunk_size=8192):
                    file.write(chunk)

        # Copy the planet extract to the Valhalla directory
        shutil.copyfile(
            raw_file,
            data_path.joinpath("germany.osm.pbf"),
        )

        # Remove any existing Valhalla builder containers
        for container in docker_client.containers.list(
            all=True, filters={"name": f"pharmalink-valhalla-builder"}
        ):
            container.remove(force=True)

        # Run Valhalla container to convert PBF file to Valhalla tiles
        builder = docker_client.containers.run(
            image="ghcr.io/gis-ops/docker-valhalla/valhalla:latest",
            detach=True,
            name="pharmalink-valhalla-builder",
            volumes=[f"{str(data_path)}:/custom_files"],
            healthcheck={
                "test": "curl -s -o /dev/null -w '%{http_code}' http://localhost:8002/status | grep -q 200 || exit 1",
                "interval": 5,
                "timeout": 1,
                "retries": 10,
                "start_period": 2,
            },
            environment={
                "build_elevation": True,
                "use_default_speeds_config": True,
                "serve_tiles": False,
            },
        )

        # Wait for Valhalla tile conversion to complete
        while (
            builder.status != "exited"
            and builder.logs(tail=1) != "INFO: Not serving tiles. Exiting."
        ):
            builder.reload()
            time.sleep(1)

        # Remove Valhalla tile builder container
        builder.remove(force=True)

        return

    def _create_valhalla_service(
        self, docker_client: docker.DockerClient, data_path: path.Path
    ):

        # Pull latest Valhalla Docker image
        docker_client.images.pull(
            "ghcr.io/gis-ops/docker-valhalla/valhalla", tag="latest"
        )

        # Remove any existing Valhalla server containers
        for container in docker_client.containers.list(
            all=True, filters={"name": "pharmalink-valhalla-server"}
        ):
            container.remove(force=True)

        container = docker_client.containers.run(
            image="ghcr.io/gis-ops/docker-valhalla/valhalla:latest",
            detach=True,
            name=f"pharmalink-valhalla-server",
            ports={8002: 8002},
            volumes=[f"{str(data_path)}:/custom_files"],
            healthcheck={
                "test": "curl -s -o /dev/null -w '%{http_code}' http://localhost:8002/status | grep -q 200 || exit 1",
                "interval": 5000000000,
                "timeout": 1000000000,
                "retries": 10,
                "start_period": 2000000000,
            },
        )

        while container.health != "healthy":
            time.sleep(0.1)
            container.reload()

        # Pause Valhalla container after successful startup
        container.stop()

        return container


def old_build_graph(force: bool = False):
    """Build the Valhalla routing graph from the OSM planet extract using the gis-ops/valhalla Docker container."""

    # Connect to Docker daemon and catch the most common exception which is caused by the Docker daemon not running
    try:
        docker_client = docker.from_env()
    except docker.errors.DockerException:
        raise Exception(
            "Could not connect to Docker daemon. Please ensure Docker is running."
        )

    # Pull latest Valhalla Docker image
    docker_client.images.pull("ghcr.io/gis-ops/docker-valhalla/valhalla", tag="latest")

    # Skip build if Valhalla routing graph already exists and is not forced
    valhalla_data = res.files(__package__).joinpath("cache", "valhalla-graph")

    if valhalla_data.exists() and not force:
        print("Valhalla routing graph found. Skipping build.")
        return

    # Build Valhalla routing graph
    print("No Valhalla routing graph found. Building now...")

    # Ensure empty cache subdirectory "valhalla" exists and contains a copy of the OSM planet-extract for Germany
    valhalla_data.mkdir(exist_ok=True, parents=True)

    # Ensure the main sources directory contains the planet-extract file
    raw_file = valhalla_data.parent.parent.joinpath("sources", "germany.osm.pbf")
    # raw_file = valhalla_data.parent.parent.joinpath("sources", "andorra-latest.osm.pbf")

    if not raw_file.exists():
        print(
            "OSM base file for Valhalla Graph generation is missing. Downloading now (~ 4GB)..."
        )

        extract_url = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"

        request = req.get(extract_url, stream=True)
        request.raise_for_status()

        file_size = int(request.headers.get("content-length", 0))

        with tqdm.wrapattr(
            open(raw_file, "wb"),
            "write",
            miniters=1,
            total=file_size,
            desc=f"Downloading {raw_file.name}",
        ) as file:
            for chunk in request.iter_content(chunk_size=8192):
                file.write(chunk)

    # Copy the planet extract to the Valhalla directory
    shutil.copyfile(
        raw_file,
        valhalla_data.joinpath("germany.osm.pbf"),
    )

    # Remove any existing Valhalla builder containers
    for container in docker_client.containers.list(
        all=True, filters={"name": f"pharmalink-valhalla-builder"}
    ):
        container.remove(force=True)

    # Run Valhalla container to convert PBF file to Valhalla tiles
    builder = docker_client.containers.run(
        image="ghcr.io/gis-ops/docker-valhalla/valhalla:latest",
        detach=True,
        name="pharmalink-valhalla-builder",
        volumes=[f"{str(valhalla_data)}:/custom_files"],
        environment={
            "build_elevation": True,
            "use_default_speeds_config": True,
            # "build_admins": True,
            # "build_time_zones": True,
            # "build_transit": True,
            "serve_tiles": False,
        },
    )

    # Wait for Valhalla tile conversion to complete
    while (
        builder.status != "exited"
        and builder.logs(tail=1) != "INFO: Not serving tiles. Exiting."
    ):
        builder.reload()
        time.sleep(1)

    # Remove Valhalla tile builder container
    # builder.remove(force=True)

    return
