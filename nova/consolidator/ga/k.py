'''
  Module for all constants used to access data structures.
'''
######
# - Metrics Tuple (<m_tuple>)
#   (<vcpus>, <ram>, <disk>)
######

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
#
# - Chromosome (<ch>):
#   [<hostname1>, <hostname2>, ...]
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
######

_BASE = 0
_CAP = 1

def get_base(host_dict, hostname):
  return host_dict[hostname][_BASE]

def get_cap(host_dict, hostname):
  return host_dict[hostname][_CAP]