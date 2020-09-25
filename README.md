# Docker development environment creator
This proyect dockerize your framework by running:

./create-env.py stack-config.json

Frameworks supported:
- Laravel with support for PHP 5.6/7.0/7.1/7.2/7.3
- Node
- React
- Java

To know how to configure your proyect, see the following example files:
- apps-stack.json
- laravel-app.json
- nodejs-app.json
- reactjs-app.json

Backend DB's supported:
- redis
- mysql
- mongo

Writen in python it requires:

. docker

. docker-compose

. git

. python3

. append user to docker group

. gitpython library(install it with pip)

At the end you have configured in /etc/hosts the aliases to see your project running