import venusian
import sys

from .swf import SWFClient, Client


__all__ = ['make_config', 'ClientConfig', 'activity_config', 'workflow_config']


def activity_config(name, version, task_list,
                    heartbeat=60,
                    schedule_to_close=420,
                    schedule_to_start=120,
                    start_to_close=300,
                    descr=None,
                    **kwargs):

    def wrapper(wrapped):
        def callback(scanner, name, obj):
            wrapped_instance = wrapped(**kwargs)
            scanner.client.register_activity(
                activity_runner=wrapped_instance,
                name=name,
                version=version,
                task_list=task_list,
                heartbeat=heartbeat,
                schedule_to_close=schedule_to_close,
                schedule_to_start=schedule_to_start,
                start_to_close=start_to_close,
                descr=descr
            )
        venusian.attach(wrapped, callback, category='activity')
        return wrapped

    return wrapper


def workflow_config(name, version, task_list,
                    execution_start_to_close=3600,
                    task_start_to_close=60,
                    child_policy='TERMINATE',
                    descr=None,
                    **kwargs):

    def wrapper(wrapped):
        def callback(scanner, name, obj):
            wrapped_instance = wrapped(**kwargs)
            scanner.client.register_workflow(
                decision_maker=wrapped_instance,
                name=name,
                version=version,
                task_list=task_list,
                execution_start_to_close=execution_start_to_close,
                child_policy=child_policy,
                descr=descr
            )
        venusian.attach(wrapped, callback, category='workflow')
        return wrapped

    return wrapper


def make_config(domain, client=None):
    return ClientConfig(Client(SWFClient(domain, client=client)))


class ClientConfig(object):
    def __init__(self, client):
        self._client = client

    def _scan(self, categories=None, package=None, ignore=None):
        scanner = venusian.Scanner(client=self._client)
        if package is None:
            package = caller_package(level=3)  # because of the scan call
        scanner.scan(package, categories=categories, ignore=ignore)

    def scan(self, package=None, ignore=None):
        self._scan(categories=('activity', 'workflow'),
                   package=package, ignore=ignore)

    def scan_activities(self, package=None, ignore=None):
        self._scan(categories=('activity'), package=package, ignore=ignore)

    def scan_workflows(self, package=None, ignore=None):
        self._scan(categories=('workflow'), package=package, ignore=ignore)

    def start_activity_loop(self, task_list):
        while 1:
            self._client.dispatch_next_activity(task_list)

    def start_workflow_loop(self, task_list):
        while 1:
            self._client.dispatch_next_decision(task_list)

    def start_test_loop(self, task_list):
        # Only use this for testing!
        while 1:
            self._client.dispatch_next_decision(task_list)
            self._client.dispatch_next_activity(task_list)


# Stolen from Pyramid

def caller_module(level=2, sys=sys):
    module_globals = sys._getframe(level).f_globals
    module_name = module_globals.get('__name__') or '__main__'
    module = sys.modules[module_name]
    return module


def caller_package(level=2, caller_module=caller_module):
    # caller_module in arglist for tests
    module = caller_module(level+1)
    f = getattr(module, '__file__', '')
    if (('__init__.py' in f) or ('__init__$py' in f)):  # empty at >>>
        # Module is a package
        return module
    # Go up one level to get package
    package_name = module.__name__.rsplit('.', 1)[0]
    return sys.modules[package_name]