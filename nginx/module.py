# -*- coding: utf-8 -*-
'''
Equal Plus
@author: Hye-Churn Jang
'''

#===============================================================================
# Import
#===============================================================================
import os
import time
import json
import shutil
import docker
import argparse
import configparser

#===============================================================================
# Implement
#===============================================================================
# load configs
path = os.path.dirname(os.path.realpath(__file__))
config = configparser.ConfigParser()
config.read(f'{path}/module.ini', encoding='utf-8')
client = docker.from_env()

# default configs
title = config['default']['title']
tenant = config['default']['tenant']
version = config['default']['version']

memory = config['default']['memory']

hostname = config['default']['hostname']
host = config['default']['host']
port = config['default']['port']
export = True if config['default']['export'].lower() == 'true' else False

system_access_key = config['default']['system_access_key']
system_secret_key = config['default']['system_secret_key']

health_check_interval = int(config['default']['health_check_interval'])
health_check_timeout = int(config['default']['health_check_timeout'])
health_check_retries = int(config['default']['health_check_retries'])

server_name = config['service']['server_name']


#===============================================================================
# Container Control
#===============================================================================
# build
def build(): client.images.build(nocache=True, rm=True, path=f'{path}', tag=f'{tenant}/{title}:{version}')


# deploy
def deploy(nowait=False):
    try: os.mkdir(f'{path}/conf.d')
    except: pass
    
    locations = ''
    upstreams = ''
    
    if 'keycloak' in config and 'location' in config['keycloak'] and 'endpoint' in config['keycloak']:
        locations = \
"""
location %s {
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Server $host;
proxy_pass http://keycloak/;
}
""" % config['keycloak']['location']
        
        upstreams = \
"""
upstream keycloak {
server %s;
}
""" % config['keycloak']['endpoint']

    if 'backends' in config:
        for location, endpoint in config['backends'].items():
            locations += \
"""
location /%s/ {
proxy_pass http://%s/%s/;
}
""" % (location, location, location)
            upstreams += \
"""
upstream %s {
server %s;
}
""" % (location, endpoint)

    locations += \
"""
location %s {
alias /publish/webroot/;
}
""" % config['publish']['location']
        
    publish_endpoint = os.path.abspath(config['publish']['endpoint'])
    
    with open(f'{path}/conf.d/nginx.conf', 'w') as fd:
        fd.write(\
"""
user root;
worker_processes 1;
events {
worker_connections 1024;
multi_accept on;
use epoll;
}
http {
include mime.types;
default_type application/octet-stream;
sendfile on;
keepalive_timeout 65;
client_max_body_size 0;
large_client_header_buffers 4 128k;
ssl_certificate_key /publish/webcert/server.key;
ssl_certificate /publish/webcert/server.crt;
ssl_session_timeout 10m;
ssl_protocols SSLv2 SSLv3 TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
# resolver 127.0.0.11 valid=2s;
proxy_buffers 4 256k;
proxy_buffer_size 128k;
proxy_busy_buffers_size 256k;
proxy_http_version 1.1;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $http_connection;
server {
listen 443 ssl;
server_name %s;
%s
}
%s
}
""" % (server_name, locations, upstreams))
    
    ports = {
        f'{port}/tcp': (host, int(port))
    } if export else {}
    
    container = client.containers.run(
        f'{tenant}/{title}:{version}',
        detach=True,
        name=f'{tenant}-{title}',
        hostname=hostname,
        network=tenant,
        mem_limit=memory,
        ports=ports,
        environment=[
        ],
        volumes=[
            f'{path}/conf.d/nginx.conf:/etc/nginx/nginx.conf',
            f'{publish_endpoint}:/publish',
        ],
        healthcheck={
            'test': 'curl -kv https://127.0.0.1 || exit 1',
            'interval': health_check_interval * 1000000000,
            'timeout': health_check_timeout * 1000000000,
            'retries': health_check_retries
        }
    )

    while not nowait:
        time.sleep(1)
        container.reload()
        print('check desire status of container')
        if container.status != 'running':
            print('container was exited')
            exit(1)
        if 'Health' in container.attrs['State'] and container.attrs['State']['Health']['Status'] == 'healthy':
            print('container is healthy')
            break


# start
def start():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): container.start()
    except: pass


# restart
def restart():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): container.restart()
    except: pass


# stop
def stop():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): container.stop()
    except: pass


# clean
def clean():
    for container in client.containers.list(all=True, filters={'name': title}): container.remove(v=True, force=True)
    shutil.rmtree(f'{path}/conf.d', ignore_errors=True)


# purge
def purge():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): container.remove(v=True, force=True)
    except: pass
    try: client.images.remove(image=f'{tenant}/{title}:{version}', force=True)
    except: pass
    shutil.rmtree(f'{path}/conf.d', ignore_errors=True)


# monitor
def monitor():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): print(json.dumps(container.stats(stream=False), indent=2))
    except: pass


# logs
def logs():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): print(container.logs(tail=100).decode('utf-8'))
    except: pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--build', action='store_true', help='build container')
    parser.add_argument('-d', '--deploy', action='store_true', help='deploy container')
    parser.add_argument('-s', '--start', action='store_true', help='start container')
    parser.add_argument('-r', '--restart', action='store_true', help='restart container')
    parser.add_argument('-t', '--stop', action='store_true', help='stop container')
    parser.add_argument('-c', '--clean', action='store_true', help='clean container')
    parser.add_argument('-p', '--purge', action='store_true', help='purge container')
    parser.add_argument('-l', '--logs', action='store_true', help='show container logs')
    parser.add_argument('-m', '--monitor', action='store_true', help='show container stats')
    parser.add_argument('-w', '--nowait', action='store_true', help='wait desire status of container')

    args = parser.parse_args()
    if not (args.logs or args.monitor):
        argCount = 0
        argCount += 1 if args.build else 0
        argCount += 1 if args.deploy else 0
        argCount += 1 if args.start else 0
        argCount += 1 if args.restart else 0
        argCount += 1 if args.stop else 0
        argCount += 1 if args.clean else 0
        argCount += 1 if args.purge else 0
        if argCount > 1 or argCount == 0: parser.print_help()

    if args.build: build()
    elif args.deploy: deploy(args.nowait)
    elif args.start: start()
    elif args.restart: restart()
    elif args.stop: stop()
    elif args.clean: clean()
    elif args.purge: purge()
    if args.monitor: monitor()
    if args.logs: logs()
