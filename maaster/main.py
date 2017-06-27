import yaml
from argparse import ArgumentParser, FileType
from maas.client import login, connect


class Maaster(object):
    def __init__(self, client):
        for i in client.spaces.list():
            print(repr(i.name))


def args():
    parser = ArgumentParser()
    parser.add_argument('--url', help='url of the maas api endpoint')
    auth = parser.add_argument_group('authentication')
    auth.add_argument('--username', help='MAAS username')
    auth.add_argument('--password', help='MAAS password')
    auth.add_argument('--apikey', help='MAAS apikey')
    commands = parser.add_subparsers(title='command')
    pull = commands.add_parser('pull')
    pull.add_argument('file', type=FileType('wb'),
                      help='file to write to, or "-" for stdout')
    push = commands.add_parser('push')
    push.add_argument('file', type=FileType('r'),
                      help='file to read from, or "-" for stdin')
    return parser.parse_args()


def main():
    opts = args()
    Maaster(connect(opts.url, apikey=opts.apikey))


if __name__ == '__main__':
    main()
