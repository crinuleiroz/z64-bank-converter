import yaml


class FlowStyleList(list):
        pass


def represent_flow_style_list(dumper, data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)


yaml.add_representer(FlowStyleList, represent_flow_style_list)
