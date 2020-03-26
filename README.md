# Mixcloud Bulk Downloader

---

## Development

### Run in Docker
Based on the info found [here](https://github.com/moby/moby/issues/8710) 

Install libraries:
```shell script
$ brew cask install xquartz
$ brew install socat
```

In a separate terminal window, set up connection between docker display and host display:
```shell script
$ socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\" &
```

Check if listener is working:
```
$ lsof -i TCP:6000
COMMAND  PID       USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
socat   1520 simonprive    5u  IPv4 0xff890ee3b20f652b      0t0  TCP *:6000 (LISTEN)
```

Run container and application
```shell script
$ docker-compose -f docker-compose.dev.yml up
```

---

## Deployment

For deployment, [Pyinstaller](https://www.pyinstaller.org/) is used to package the 
application per platform.

### Linux & MacOS
1. Make sure you have `PyInstaller` installed
2. From the project's root directory, run the following command: 
```shell script
$ pyinstaller --windowed --onefile app/main.py
```

The Linux version can also be built inside a Docker container.

### Windows
TBD
