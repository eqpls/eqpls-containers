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

container_links = config._sections['container:links']


#===============================================================================
# Container Control
#===============================================================================
# build
def build(): client.images.build(nocache=True, rm=True, path=f'{path}', tag=f'{tenant}/{title}:{version}')


# deploy
def deploy(nowait=False):
    try: os.mkdir(f'{path}/conf.d')
    except: pass
    try: os.mkdir(f'{path}/data.d')
    except: pass
    try: os.mkdir(f'{path}/back.d')
    except: pass

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
        links=container_links,
        ports=ports,
        environment=[
            f'discovery.type=single-node'
        ],
        volumes=[
            f'{path}/conf.d:/conf.d',
            f'{path}/data.d:/usr/share/elasticsearch/data',
            f'{path}/back.d:/back.d'
        ],
        healthcheck={
            'test': 'curl -k https://localhost:9200 || exit 1',
            'interval': health_check_interval * 1000000000,
            'timeout': health_check_timeout * 1000000000,
            'retries': health_check_retries
        },
        restart_policy={
            'Name': 'on-failure',
            'MaximumRetryCount': 5
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
            container.exec_run(f'/usr/share/elasticsearch/bin/elasticsearch-users useradd {system_access_key} -p {system_secret_key} -r superuser -s')
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
    shutil.rmtree(f'{path}/data.d', ignore_errors=True)


# purge
def purge():
    try:
        for container in client.containers.list(all=True, filters={'name': title}): container.remove(v=True, force=True)
    except: pass
    try: client.images.remove(image=f'{tenant}/{title}:{version}', force=True)
    except: pass
    shutil.rmtree(f'{path}/conf.d', ignore_errors=True)
    shutil.rmtree(f'{path}/data.d', ignore_errors=True)


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
