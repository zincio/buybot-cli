import click

@click.group()
def orders():
    pass

@orders.command()
def ls():
    pass

@greet.command()
@click.option('id', help='The id of the order you wish to retry')
def retry(order_id):
    pass



if __name__ == '__main__':
    greet()