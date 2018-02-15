from __future__ import print_function

import os
import socket
import time
try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser
try:
    from urllib.parse import urljoin
except ImportError:
    from urllib import urljoin

import click
import requests

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
def orders():
    pass

@click.command()
def whoami():
    resp = api_call('/v0/users/current')
    resp.raise_for_status()
    click.echo("You are: %s" % resp.json()['name'])

@click.command()
def login():
    sess = requests.Session()

    # Start a login request
    resp = sess.post(urljoin(BUYBOT_URL, '/cli/auth'), params={'hostname': socket.gethostname()}, timeout=31)
    resp.raise_for_status()

    browser_url = resp.json()['browser_url']
    poll_url = resp.json()['poll_url']

    click.echo("Please open the following URL in your browser:\n    %s\n" % browser_url)

    while True:
        resp = sess.get(poll_url, timeout=31)

        if resp.status_code == 404:
            # rejected :(
            click.echo("Authorization rejected :(")
            return

        js = resp.json()
        if js.get('token') and js.get('user_id'):
            CFG['auth.user_id'] = js['user_id']
            CFG['auth.token'] = js['token']
            write_config(CFG)
            click.echo("Login complete!")
            return

        elif js.get('pending'):
            click.echo("Authorization pending...")

        else:
            click.echo("Unknown error. Trying again...")

        time.sleep(5)

@orders.command()  # buybot orders ls
def ls():
    pass

@orders.command()
@click.argument('id')
def retry(order_id):
    pass

cli.add_command(orders)
cli.add_command(login)
cli.add_command(whoami)

if __name__ == '__main__':
    CFG = read_config()
    cli()
