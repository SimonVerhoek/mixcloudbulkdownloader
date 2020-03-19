## To run in Docker:

Install libraries:
```
$ brew cask install xquartz
$ brew install socat
```

In a separate terminal window, set up connection between docker display and host display:
```
$ socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\" &
```

Check if listener is working:
```
lsof -i TCP:6000
COMMAND  PID       USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
socat   1520 simonprive    5u  IPv4 0xff890ee3b20f652b      0t0  TCP *:6000 (LISTEN)
```

Run container and application
```
docker run -e DISPLAY=docker.for.mac.host.internal:0 MBDLR
```

more info [here](https://github.com/moby/moby/issues/8710)
