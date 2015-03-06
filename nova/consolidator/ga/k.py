'''
  Module for all constants used to access data structures.
'''

# def check_metrics_tuple(metrics_tuple):
#   '''
#     Generic metrics tuple:
#       (vcpus_*, ram_*, disk_*)
#   '''
#   t = type(metrics_tuple)
#   assert t is tuple, '{} is not a tuple'.format(t)
#   l = len(metrics_tuple)
#   assert l == 3, 'Metrics tuple must have 3 elements ({})'.format(l)
#   t = type(metrics_tuple[_VCPUS])
#   assert t is int, '(vcpu) {} is not int'.format(t)
#   t = type(metrics_tuple[_RAM])
#   assert t is int, '(ram) {} is not int'.format(t)
#   t = type(metrics_tuple[_DISK])
#   assert t is int, '(disk) {} is not int'.format(t)

# def check_out(out):
#   '''
#     Output tuple:
#       (hostname, [instance_ids])
#   '''
#   t = type(out)
#   assert t is tuple, '(out) {} is not a tuple'.format(t)
#   l = len(out)
#   assert l == 2, 'Out tuple must have 2 elements ({})'.format(l)
#   t = type(out[_HOSTNAME])
#   assert t is str, '(hostname) {} is not str'.format(t)
#   t = type(out[_INSTANCE_IDS])
#   assert t is list, '(instance ids) {} is not list'.format(t)
#   for i_id in out[_INSTANCE_IDS]:
#     t = type(i_id)
#     assert t is int, '(instance id) {} is not int'.format(t)

###### Metrics
_VCPUS = 0
_RAM = 1
_DISK = 2

def get_vcpus(metrics_tuple):
  return metrics_tuple[_VCPUS]

def get_ram(metrics_tuple):
  return metrics_tuple[_RAM]

def get_disk(metrics_tuple):
  return metrics_tuple[_DISK]

###### Genetic Data Structures
# - Metrics Tuple (<m_tuple>)
#   (<vcpus>, <ram>, <disk>)
#
# - Gene (<gene>)
#   {
#     'instances': [<i_id>, <i_id>, ...],
#     'status': <m_tuple>,
#     'cap': <m_tuple>
#   }
#
# - Chromosome (<ch>):
#   {
#     hostname1: <gene>,
#     hostname2: <gene>,
#     ...
#   }
#
# - Population (<pop>)
#   [<ch>, <ch>, ...]
#
###### Base Core Structures
# - Hosts Dict
#   {
#     hostname1: (<m_tuple>, <m_tuple>),
#     hostname2: (<m_tuple>, <m_tuple>),
#     ...
#   }
#
# - Instances Dict
#   {
#     i_id: <m_tuple>,
#     i_id: <m_tuple>,
#     ...
#   }

_BASE = 0
_CAP = 1
INSTANCE_IDS = 'instances'
STATUS = 'status'
CAP = 'cap'

def get_base(host_dict, hostname):
  return host_dict[hostname][_BASE]

def get_cap(host_dict, hostname):
  return host_dict[hostname][_CAP]

def get_cap_from_ch(chromosome, hostname):
  return chromosome[hostname][CAP]

def get_instance_ids(chromosome, hostname):
  return chromosome[hostname][INSTANCE_IDS]

def get_status(chromosome, hostname):
  return chromosome[hostname][STATUS]