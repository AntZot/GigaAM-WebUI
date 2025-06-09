# GigaAM-WebUI

A browser interface for [salute-developers/GigaAM](https://github.com/salute-developers/GigaAM/blob/main/README_ru.md).

uvicorn src.main:app --reload

- ## Running with Docker 

1. Install and launch [Docker-Desktop](https://www.docker.com/products/docker-desktop/).

2. Git clone the repository

```sh
git clone https://github.com/AntZot/GigaAM-WebUI.git
```

3. Build the image 

```sh
docker compose build 
```

4. Run the container 

```sh
docker compose up
```

5. Connect to the WebUI with your browser at `http://localhost:8000`
