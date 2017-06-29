import yaml
from argparse import ArgumentParser, FileType
from maas.client import connect, bones


class Maaster(object):
    def __init__(self, client, fd):
        self.client = client
        self.fd = fd
        self.writing = hasattr(fd, 'write')
        self.related = {}

    def __rewrite_related(self, dict_):
        for name, value in dict_.items():
            if name in self.related:
                dict_[name] = self.related[name][value]
        return dict_

    def __upload(self, type, definition, key_facet='name', defaults=None):
        mapping = {}
        if type is None:
            return mapping
        for key, values in definition.items():
            create = {}
            if defaults is not None:
                create.update(defaults)
            create.update(values)
            create = self.__rewrite_related(create)
            create[key_facet] = key
            try:
                mapping[key] = type.create(**create)
            except bones.CallError:
                print('err, already exists')
                vlan = self.client.vlans.get(fabric=11, vid=0)
                print(vlan.mtu)

        return mapping

    def __delete_all_vlans(self):
        for fabric in self.client.fabrics.list():
            for vlan in self.client.vlans.list(fabric):
                try:
                    vlan.delete()
                except:
                    pass

    def __delete_all(self):
        self.__delete_all_vlans()
        endpoints = [self.client.subnets, self.client.fabrics,
                     self.client.spaces]
        for endpoint in endpoints:
            for item in endpoint.list():
                try:
                    item.delete()
                except:
                    pass

    def partition_children(self, dict, child):
        if dict is None:
            return None, {}
        cleaned_parent = {}
        children = {}
        for key, values in dict.items():
            child_value = values.pop(child, None)
            if child_value is not None:
                children[key] = child_value
            cleaned_parent[key] = values
        return cleaned_parent, children

    def push(self):
        infra = yaml.load(self.fd)
        if 'networks' not in infra:
            return
        self.__delete_all()
        networks = infra['networks']
        self.related['space'] = self.__upload(
            self.client.spaces, networks.get('spaces'))

        fabrics, dirty_vlans = self.partition_children(
            networks.get('fabrics'), 'vlans')
        self.related['fabrics'] = self.__upload(self.client.fabrics, fabrics)
        for fabric_name, vlans in dirty_vlans.items():
            fabric = self.related['fabrics'][fabric_name]
            clean_vlans, dirty_subnets = self.partition_children(
                vlans, 'subnets')
            vlans = self.__upload(
                self.client.vlans, clean_vlans, key_facet='vid',
                defaults={'fabric': fabric})
            for vlan_name, subnets in dirty_subnets.items():
                vlan = vlans[vlan_name]
                clean_subnets, dirty_ranges = self.partition_children(
                    subnets, 'reserved')
                subnets = self.__upload(
                    self.client.subnets, clean_subnets, key_facet='cidr',
                    defaults={'fabric': fabric, 'vlan': vlan})


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
    Maaster(connect(opts.url, apikey=opts.apikey), opts.file).push()


if __name__ == '__main__':
    main()
