#!/usr/bin/env python3
import glob
import json
import os
import git
import sys
import shutil
from shutil import copyfile
from git import RemoteProgress
from subprocess import Popen, PIPE, check_output
import pathlib

nginxSites = []
proxyStrategy = "standard"

DOCKER_UP = "docker-compose -p {} up -d --build"
SCRIPT_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))

COMPOSE_YML = SCRIPT_PATH + '/docker-compose.yml'

NGINX_PATH = SCRIPT_PATH + "/nginx/"
NGINX_CONF = NGINX_PATH + "conf.d/"

VOLUME_STR = "{}:{}"

DB_PORTS = {
    "redis": "6379",
    "mongo": "27017",
    "mysql": "3306"
}

DB_DATA_PATH = {
    "mysql": "/var/lib/mysql",
    "redis": "/data",
    "mongo": "/data/db"
}

QUEUE_PORTS = {
    "rabbitmq": "15672"
}

QUEUE_DATA_PATH = {
    "rabbitmq": "/var/lib/rabbitmq"
}

DB_VOLUME = "~/.dockerize/data/{}"
QUEUE_VOLUME = "~/.dockerize/data/{}"

def printMessage(msg):
    msgLen = len(msg) + 10
    print( "-" * msgLen)
    print( "|    " + msg + "    |")
    print( "-" * msgLen + "\n")

class CloneProgress(RemoteProgress):
    def update(
        self,
        op_code,
        cur_count,
        max_count=None,
        message=''
    ):
        if message:
            print(message)

def cloneAppCode(from_repo, to_local_dir):
    printMessage("Cloning project: " + from_repo + ' into folder: ' + to_local_dir)
    if not os.path.isdir(to_local_dir):
        try:
            git.Repo.clone_from(from_repo, to_local_dir, branch='master', progress=CloneProgress() )
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    else:
        print("Repo already exists!")

    printMessage("Clone Completed")


def parseConfigJson( config_file ):
    global proxyStrategy
    printMessage("Parsing " + config_file)
    data = None

    try:
        with open(config_file) as appsConfigfile:
            data = json.load( appsConfigfile )
    except Exception as e:
        print("Config File Error: ", e)
        sys.exit(1)

    repos = data['repos'] if "repos" in data else []
    dbs = data['dbs'] if "dbs" in data else []
    custom = data['custom'] if "custom" in data else []
    queues = data['queues'] if "queues" in data else []
    if "proxyStrategy" in data:
        proxyStrategy = data['proxyStrategy']

    print ("DONE!\n\n")
    return data['project'], repos, dbs, custom, queues


def json2yaml(json, level=0):
    spaces = "  "
    new_line = "\n"
    to_print = ""
    for key, value in json.items():

        to_print += (spaces*level) + key + ":"
        vType = type(value)

        if vType is dict:
            to_print += "\n" + json2yaml(value, level+1)
        elif vType is list:
            for item in value:
                to_print += new_line + (spaces*level+spaces) + "- " + item
            to_print += new_line
        else:
            to_print += " " + value + new_line

    return to_print


def parseDomains(repo):
    if "domains" in repo:
        domain = repo['mainDomain']
    else:
        domain = repo['name'] + '.app'

    if proxyStrategy == "inner":
        domain += ".inner"
    else:
        # Assumes standard
        pass

    return domain


def writeLaravelService(project, repo, version):
    try:
        file = open(COMPOSE_YML, 'a')
        repoName = repo['name']
        repoPath = repo['path']
        aliases = []

        aliases.append(parseDomains(repo))
        print(version)
        dataToWrite = {
            repoName: {
		        "build": 
                        "./laravel/5.6/" if version == 5 
                        else "./laravel/7.0/" if  version == 70 
                        else "./laravel/7.1/" if  version == 71
                        else "./laravel/7.0/" if  version == 72
                        else "./laravel/5.6/",
                "working_dir": "/var/www/" + repoName,
                "volumes": [
                    repoPath + ":/var/www/" + repoName
                ],
                "networks": {
                    project: {
                        "aliases": aliases
                    }
                }
            }
        }

        if "hostname" in repo:
            dataToWrite[repoName]["hostname"] = repo["hostname"]

        file.write(os.linesep + os.linesep + json2yaml(dataToWrite, 1))
        
    except Exception as e:
        print("Write Laravel Service Error ("+ project +"):", e)
        sys.exit(1)
    finally:
        if file:
            file.close()


def writeJavaService(project, repo):
    printMessage("Writing Java Service")
    try:
        file = open(COMPOSE_YML, 'a')
        repoName = repo['name']
        repoPath = repo['path']
        aliases = []

        aliases.append(parseDomains(repo))

        dataToWrite = {
            repoName: {
                "build": {
                    "context": repoPath,
                    "dockerfile": SCRIPT_PATH + "/java/Dockerfile"
                },
                "working_dir": "/usr/src/app/",
                "networks": {
                    project: {
                        "aliases": aliases
                    }
                }
            }
        }
        if "hostname" in repo:
            dataToWrite[repoName]["hostname"] = repo["hostname"]

        file.write(os.linesep * 2 + json2yaml(dataToWrite, 1))
        print ("DONE!\n\n")
    except Exception as e:
        print ("Write Java Service Error ("+ project +"):", e)
        sys.exit(1)
    finally:
        if file:
            file.close()


def writeNodeJSService(project, repo):
    printMessage("Writing NodeJS Service")
    try:
        file = open(COMPOSE_YML, 'a')
        repoName = repo['name']
        repoPath = repo['path']
        aliases = []

        aliases.append(parseDomains(repo))

        dataToWrite = {
            repoName: {
                "build": {
                    "context": repoPath,
                    "dockerfile": SCRIPT_PATH + "/nodejs/Dockerfile"
                },
                "working_dir": "/usr/src/app/",
                "volumes": [
                    VOLUME_STR.format(repoPath, "/usr/src/app"),
                    '/usr/src/app/node_modules'
                ],
                "networks": {
                    project: {
                        "aliases": aliases
                    }
                }
            }
        }
        if "hostname" in repo:
            dataToWrite[repoName]["hostname"] = repo["hostname"]

        file.write( os.linesep * 2 + json2yaml(dataToWrite, 1) )
        print("DONE!\n\n")
    except Exception as e:
        print("Write NodeJS Service Error ("+ project +"):", e)
        sys.exit(1)
    finally:
        if file:
            file.close()

def writeReactJSService(project, repo):
    printMessage("Writing ReactJS Service")
    reactfile = repo['path'] + "/nginx/react-nginx.conf"
    try:
        with open(reactfile) as file:
            print("\n\nNginx react template created \n\n")
            file.close()
            pass
    except IOError as e:
        print ("Unable to open file " + reactfile + '\n') #Does not exist OR no read permissions
        shutil.copytree(SCRIPT_PATH + "/reactjs/nginx", repo['path'] + "/nginx")
    
    try:
        file = open(COMPOSE_YML, 'a')
        repoName = repo['name']
        repoPath = repo['path']
        aliases = []

        aliases.append(parseDomains(repo))

        dataToWrite = {
            repoName: {
                "build": {
                    "context": repoPath,
                    "dockerfile": SCRIPT_PATH + "/reactjs/Dockerfile"
                },
                "working_dir": "/app/",
                "volumes": [
                    VOLUME_STR.format(repoPath, "/app"),
                    '/app/node_modules'
                ],
                "networks": {
                    project: {
                        "aliases": aliases
                    }
                }
            }
        }
        if "hostname" in repo:
            dataToWrite[repoName]["hostname"] = repo["hostname"]

        file.write( os.linesep * 2 + json2yaml(dataToWrite, 1) )
        
            
        print("DONE!\n\n")
    except Exception as e:
        print("Write NodeJS Service Error ("+ project +"):", e)
        sys.exit(1)
    finally:
        if file:
            file.close()

def writeAppDetailsIntoComposeFile(project, app_description):
    rType = app_description['framework']

    if "domains" in app_description:
        mainDomain = app_description['domains'].split()[0]
        data = {
            "domains": app_description['domains'],
            "mainDomain": mainDomain,
            "name": app_description['name'],
            "rType": rType
        }
        nginxSites.append(data)
        app_description['mainDomain'] = mainDomain

    if "nodejs" in rType:
        writeNodeJSService(project, app_description)
    elif "reactjs" in rType:
        writeReactJSService(project, app_description)
    elif "java" in rType:
        writeJavaService(project, app_description)
    elif "laravel" in rType:
        if "5.x" in rType:
            writeLaravelService(project, app_description, 5)
        elif "7.0" in rType:
            writeLaravelService(project, app_description, 70)
        elif "7.1" in rType:
            writeLaravelService(project, app_description, 71)
        elif "7.2" in rType:
            writeLaravelService(project, app_description, 72)
        else:
            print("No php version available to build this project: " + rType)

def dockerComposeFileInit():
    with open(COMPOSE_YML, 'w') as file:
        file.write("version: '2'\n")
        file.write("services:\n")


def cleanOldNginxConfs():
    printMessage('Cleaning old nginx .conf files')
    #map(os.unlink, glob.glob(NGINX_CONF + '*.conf'))
    for conf in glob.glob(NGINX_CONF + '*.conf'):
        print("Removing config file: %s \n\n" % conf)
        os.unlink(conf)

    print ("DONE!\n\n")


def processPlugins(project, repo):
    printMessage('Running plugins for ' + repo['name'])
    if "plugins" in repo:
        plugins = repo['plugins']
        path = repo['path']
        name = repo['name']
        rType = repo['framework']
        for plugin in plugins:
            if plugin == "laravel":
                laravelPlugin = './plugins/laravel.sh %s %s %s %s'
                version = rType.split("|")[1]
                os.system(laravelPlugin % (path, project, name, version))
            elif plugin == "composer":
                composerPlugin = './plugins/composer.sh %s'
                os.system(composerPlugin % (path))

    print('\nDONE!\n\n')


def createNginxConfs():
    printMessage('Creating nginx .conf files')
    if len(nginxSites) > 0:
        if not os.path.isdir(NGINX_CONF):
            os.mkdir(NGINX_CONF, 0o755)

        for nginxSite in nginxSites:
            domains = nginxSite['domains']
            name = nginxSite['name']
            mainDomain = nginxSite['mainDomain']
            rType = nginxSite['rType']

            if proxyStrategy == "inner":
                mainDomain += '.inner'
            else:
                # Assumes standard
                pass

            src = NGINX_PATH + "vhost.{}.template".format(rType.split("|")[0])
            dst = NGINX_CONF + name + ".conf"
            copyfile(src, dst)

            sed_vhost = "sed -i.bak 's/{{ %s }}/%s/g' %s"
            os.system(sed_vhost % ("domains", domains, dst))
            os.system(sed_vhost % ("domain", mainDomain, dst))
            os.system(sed_vhost % ("repo", name, dst))

            map(os.unlink, glob.glob(NGINX_CONF + '*.bak'))

    print("DONE!\n\n")

def writeNginxCompose(project):
    printMessage('Writing Nginx into docker-compose.yml')
    if len(nginxSites):
        try:
            volumesLink = []
            mainDomains = []
            for nginxSite in nginxSites:
                volumesLink.append(nginxSite['name'])
                mainDomains.append(nginxSite['mainDomain'])

            dataToWrite = {
                "nginx-proxy": {
                    "image": "nginx:1.10",
                    "ports": [
                        "80:80"
                    ],
                    "volumes_from": volumesLink,
                    "links": volumesLink,
                    "volumes": [
                        VOLUME_STR.format("./nginx/conf.d", "/etc/nginx/conf.d")
                    ]
                }
            }

            if proxyStrategy == "inner":
                dataToWrite['nginx-proxy']['networks'] = {
                    project: {
                        "aliases": mainDomains
                    }
                }
            else:
                # Assumes standard
                dataToWrite['nginx-proxy']['networks'] = [project]

            with open(COMPOSE_YML, 'a') as file:
                file.write( os.linesep + json2yaml(dataToWrite, 1) )
            print("DONE!\n\n")
        except Exception as e:
            print("Write Nginx Compose: ", e)
            sys.exit(1)


def writeNetworkCompose(project):
    printMessage('Writing networks into docker-compose.yml')
    try:
        dataToWrite = {
            "networks": {
                project: {
                    "driver": "bridge"
                }
            }
        }
        with open(COMPOSE_YML, 'a') as file:
            file.write( os.linesep + json2yaml(dataToWrite) )
        print("DONE!\n\n")
    except Exception as e:
        print("Write Network Compose:", e)
        sys.exit(1)


def writeEtcHosts(project):
    printMessage('Overriding /etc/hosts')
    if len(nginxSites):
        sites = ""
        for nginxSite in nginxSites:
            sites += nginxSite['domains'] + " "

        sed = "sudo sed -i.bak '/%s/d' /etc/hosts > /dev/null"
        tee = "echo '%s' | sudo tee -a /etc/hosts > /dev/null"

        oldLine = ".*"+project+"-docker.*"
        newLine = "127.0.0.1 " + sites + "#" + project + "-docker"

        os.system( sed % (oldLine) )
        os.system( tee % (newLine) )
    print("DONE!\n\n")


def writeDBCompose(project, dbs):
    printMessage('Writing dbs into docker-compose.yml')
    if len(dbs):
        try:
            for db in dbs:
                volume = DB_VOLUME.format(db)
                dataToWrite = {
                    db: {
                        "build": "./" + db + "/",
                        "networks": {
                            project: {
                                "aliases": [
                                    db + ".db"
                                ]
                            }
                        },
                        "volumes": [
                            VOLUME_STR.format(volume, DB_DATA_PATH[db])
                        ],
                        "ports": [
                            "0.0.0.0:" + DB_PORTS[db]+":"+DB_PORTS[db]
                        ]
                    }
                }
                with open(COMPOSE_YML, 'a') as file:
                    file.write( os.linesep + json2yaml(dataToWrite, 1) )
        except Exception as e:
            print("Write dbs into docker-compose.yml Error:", e)
            sys.exit(1)
    
    print("DONE!\n\n")

def writeQueuesCompose(project, queues):
    printMessage('Writing dbs into docker-compose.yml')
    if len(queues):
        try:
            for queue in queues:
                volume = QUEUE_VOLUME.format(queue)
                dataToWrite = {
                    queue: {
                        "build": "./" + queue + "/",
                        "image": "harbur/rabbitmq-cluster" if queue == "rabbitmq" else "",
                        "networks": {
                            project: {
                                "aliases": [
                                    queue + ".qsrv"
                                ]
                            }
                        },
                        "volumes": [
                            VOLUME_STR.format(volume, QUEUE_DATA_PATH[queue])
                        ],
                        "ports": [
                            "0.0.0.0:" + QUEUE_PORTS[queue] + ":" + QUEUE_PORTS[queue]
                        ]
                    }
                }
                with open(COMPOSE_YML, 'a') as file:
                    file.write( os.linesep + json2yaml(dataToWrite, 1) )
        except Exception as e:
            print("Write dbs into docker-compose.yml Error:", e)
            sys.exit(1)
    
    print("DONE!\n\n")

def writeCustoms(project, custom):
    printMessage('Writing custom into docker-compose.yml')
    try:
        for service in custom:
            with open(COMPOSE_YML, 'a') as file:
                file.write( os.linesep + json2yaml(service, 1) )

    except Exception as e:
        print("Write Custom Compose Error:", e)
        sys.exit(1)

    print("DONE!\n\n")

def startContainers(project):
    printMessage('Starting containers')
    os.system(DOCKER_UP.format(project))
    print("\nDONE!\n\n")

if __name__ == "__main__":
    # Get Configuration items from json details file
    project, appslist, dbsbackend, custom, queues = parseConfigJson( sys.argv[1] )
    
    # Start writing our docker-compose.yml file
    dockerComposeFileInit()
    
    for app in appslist:
        # Check if we have created our app stack directory
        app['path'] = str(check_output(['echo {}'.format(app['into'])],shell=True).strip(), 'utf-8')
        
        # Clone projects into application path defined    
        cloneAppCode(app['repository'], app['path'])
        
        # Write application details into docker-compose.yml file
        writeAppDetailsIntoComposeFile(project, app)
    # Remove older configurations for nginx into conf.d directory        
    cleanOldNginxConfs()
    # Creates  new vhost configuration files to access your micreservices trough any web browser
    createNginxConfs()
    # Append nginx to docker-compose.yml file
    writeNginxCompose(project)
    # Append databases for your project to docker-compose.yml file
    writeDBCompose(project, dbsbackend)
    # Append your queue server required for your project to docker-compose.yml file
    writeQueuesCompose(project, queues)
    # If you have included some custom image it's append to docker-compose.yml file
    writeCustoms(project, custom)
    # Append network configuration for our stack
    writeNetworkCompose(project)
    # Creates Aliases for your projects in /etc/hosts file so you can browser your services 
    # with locals dns 
    writeEtcHosts(project)
    # Finally it creates your defined stack
    startContainers(project)
    # Apply some post configuration if required
    for app in appslist:
        processPlugins(project, app)
