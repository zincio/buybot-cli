#!/usr/bin/env python
from __future__ import print_function

import os
import socket
import time
import json
try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

import click
import requests
from tabulate import tabulate

APP_NAME = 'buybot-cli'
BUYBOT_URL = os.getenv('BUYBOT_URL', 'https://buybot.zinc.io/')

def read_config():
    cfg = os.path.join(click.get_app_dir(APP_NAME), 'config.ini')
    parser = ConfigParser.RawConfigParser()
    parser.read([cfg])
    rv = {}
    for section in parser.sections():
        for key, value in parser.items(section):
            rv['%s.%s' % (section, key)] = value
    return rv

def write_config(rv):
    parser = ConfigParser.RawConfigParser()
    sections = set()
    for k in rv:
        sec, key = k.split('.')
        if sec not in sections:
            parser.add_section(sec)
            sections.add(sec)
        parser.set(sec, key, rv[k])
    try:
        os.makedirs(click.get_app_dir(APP_NAME))
    except Exception:
        pass
    cfg = os.path.join(click.get_app_dir(APP_NAME), 'config.ini')
    with open(cfg, 'w') as f:
        parser.write(f)

def api_call(url, method='GET', session=None, headers=None, **kwargs):
    if session is None:
        session = requests.Session()

    if headers is None:
        headers = {}
    headers['Authorization'] = 'Bearer ' + CFG['auth.token']

    resp = session.request(method=method, url=urljoin(BUYBOT_URL, url), headers=headers, **kwargs)
    return resp

@click.group()
def cli():
    pass

@click.group()
def products():
    pass

@click.command()
def whoami():
    resp = api_call('/v0/users/current')
    resp.raise_for_status()
    click.echo("You are: %s" % resp.json()['name'])

@click.command()
def login():
    # Start a login request
    resp = requests.post(urljoin(BUYBOT_URL, '/cli/auth'), params={'hostname': socket.gethostname()}, timeout=31)
    resp.raise_for_status()

    browser_url = resp.json()['browser_url']
    poll_url = resp.json()['poll_url']

    click.echo("Please open the following URL in your browser:\n    %s\n" % browser_url)
    click.echo("Authorization pending...", nl=False)

    while True:
        resp = requests.get(poll_url, timeout=31)

        if resp.status_code == 404:
            # rejected :(
            click.echo("\nAuthorization rejected :(")
            return

        js = resp.json()
        if js.get('token') and js.get('user_id'):
            CFG['auth.user_id'] = js['user_id']
            CFG['auth.token'] = js['token']
            write_config(CFG)
            click.echo("\nLogin complete!")
            return

        elif js.get('pending'):
            click.echo(".", nl=False)
        else:
            click.echo("\nUnknown error. Trying again...")

        time.sleep(5)

def ls(all=False, ids=None):
    resp = api_call('/v0/products')
    resp.raise_for_status()
    resp = resp.json()
    if ids:
        rows = [p for p in resp if p['id'] in ids]
    else:
        rows = [p for p in resp if all or p['user']['id'] == CFG['auth.user_id']]
    rows = [[
        p['id'],
        p['state'],
        p['user'].get('email') or p['user']['id'],
        "${0:.2f}".format(p['price']/100),
        p.get('details',{}).get('value',{}).get('title','None')[:40],
        'https://www.amazon.com/-/dp/{}'.format(p['product_id']),
    ] for p in rows]
    click.echo(tabulate(rows, headers=['ID', 'APPROVAL', 'USER', 'PRICE', 'TITLE', 'URL']))

@products.command(name="ls")
@click.option('--all', '-a', is_flag=True)
def _ls(all=False):
    ls(all=all)

@products.command()
@click.argument('ids', nargs=-1)
def approve(ids):
    resp = api_call('/v0/products/approve', method="POST", json={
        "ids":ids,
        "attempt":False,
    })
    if resp.status_code == 400:
        click.echo(resp.json()['message'], err=True)
        return
    resp.raise_for_status()
    ls(ids=ids)
    #click.echo(json.dumps(resp, indent=2))


@products.command()
@click.argument('ids', nargs=-1)
def reject(ids):
    resp = api_call('/v0/products/reject', method="POST", json={
        "ids":ids,
        "attempt":False,
    })
    if resp.status_code == 400:
        click.echo(resp.json()['message'], err=True)
        return
    resp.raise_for_status()
    ls(ids=ids)

#@products.command()
#@click.argument('id')
#def retry(order_id):
#    pass

cli.add_command(products)
cli.add_command(login)
cli.add_command(whoami)

if __name__ == '__main__':
    CFG = read_config()
    cli()
