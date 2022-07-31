# DuraPy

A service container for a service-oriented architecture approach to (neuroscience) experiments.

## Introduction

DuraPy is an open-source Python service container for neuroscience experiments utilizing a service-oriented architecture, aiming to provide the communication and process backends for each microservice. DuraPy, at its core, utilizes an event-driven paradigm: “commands” can be sent from any service and are broadcast to all services. Each command can have its own structure, and per-command handlers can be installed in each service that calls a specified function when receiving a command, enabling each service to perform custom functionality per command. As part of its service architecture, each DuraPy service runs in its own long-running process, with commands likely sent by the experimenter to initiate and terminate experiments.

In addition, a web-based graphical user interface (GUI), running itself as a DuraPy microservice, is provided to enable experimenter control of the experiment, a core feature often underestimated for modern experiments. In addition to supporting the sending and displaying of commands, managing service deployment, and viewing logging, the web GUI implementation, built on an open-source web framework [Tornado](https://github.com/tornadoweb/tornado), is explicitly designed to enable extensions, where experimenters can more easily build custom web pages for experiment monitoring or review.

Experimenters can configure custom database engines for storing/retrieving of commands. By default, the command database utilizes [Redis](https://redis.io), an open-source in-memory database, but future changes could enable DuraPy to utilize other existing networked communication frameworks.

In addition, logging infrastructure, Git-based deployment commands via the webserver and command line, and POSIX-compatible run scripts (via systemctl) are provided.

## Installation

The current method of installation is to simply clone this repository and place it on your PYTHONPATH, and begin extending.

## Tutorial

See the `example` and `pingpong` directories for examples on how to utilize DuraPy. The `example` implementation starts up, calls a few commands, and then terminates itself. This example only utilizes an in-memory database as a command database, and so is only suitable for showing how to configure a barebones process & webserver.

The `pingpong` example contains two different DuraPy processes, `pinger` and `ponger`, where once a session is initiated, the `pinger` sends "ping" commands, to which the `ponger` responds with derived "pong" commands. To run the `pingpong` example, in addition to running the `pinger` and `ponger` processes, run the `webserver` process via `pingpong/webserver/webserver.py` and issue an InitiateSessionCommand. To stop it, issue an EndSessionCommand. This `pingpong` example utilizes a Redis command database expected to be running at its default location (localhost at port 6379).
