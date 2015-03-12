from oslo_log import log as logging
LOG = logging.getLogger(__name__)

class Node(object):
  def __init__(self, node):
    self.hostname = node.host
    self.vcpus = node.vcpus
    self.ram = node.memory_mb
    self.disk = node.local_gb
    self.vcpus_used = node.vcpus_used
    self.ram_used = node.memory_mb_used
    self.disk_used = node.local_gb_used
    self.instances = {i.id: Instance(i) for i in node.instances_migrable}

  def __repr__(self):
    return '{} -> load: {}'.format(self.hostname, self.sorting_key)

  def suitable(self, instance):
    return self.vcpus - self.vcpus_used >= instance.vcpus \
      and self.ram - self.ram_used >= instance.ram \
      and self.disk - self.disk_used >= instance.disk

  def add(self, instance):
    self.vcpus_used += instance.vcpus
    self.ram_used += instance.ram
    self.disk_used += instance.disk
    self.instances[instance.id] = instance

  def remove(self, instance):
    self.vcpus_used -= instance.vcpus
    self.ram_used -= instance.ram
    self.disk_used -= instance.disk
    del self.instances[instance.id]

  @property
  def sorting_key(self):
    return 0.3 * \
      (float(self.vcpus_used) / self.vcpus + \
      float(self.ram_used) / self.ram + \
      float(self.disk_used) / self.disk)

class Instance(object):
  def __init__(self, instance):
    self.id = instance.id
    self.vcpus = instance.vcpus
    self.ram = instance.memory_mb
    self.disk = instance.root_gb

  def __repr__(self):
    return '{} -> weight: {}'.format(self.id, self.sorting_key)

  @property
  def sorting_key(self):
    return self.vcpus + self.ram + self.disk

class Holistic(object):

  def __init__(self, snapshot):
    super(Holistic, self).__init__()

    assert len(snapshot.nodes) > 0, 'Cannot init Holistic. No nodes given.'
    assert len(snapshot.instances_migrable) > 0, 'Cannot init Holistic. No migrable instance.'

    self._host_dict = {node.host: Node(node) for node in snapshot.nodes}
    self._sorted_nodes = sorted(self._host_dict.values(), key=lambda n: n.sorting_key, reverse=True)
    self._new_state = {i.id: i.host for i in snapshot.instances_migrable}
    self._no_used = len(filter(lambda n: n.vcpus_used > 0, snapshot.nodes))

  def _get_suitable_hostname(self, instance, start_index):
    hosts = self._sorted_nodes[start_index:]
    for host in hosts:
      if host.suitable(instance): return host.hostname
    return None

  def run(self):
    no_released = 0
    no_nodes = len(self._sorted_nodes)

    LOG.debug('FROM\n')
    LOG.debug('\n'.join([str(node) for node in self._sorted_nodes]))
    LOG.debug('\n')

    index = 1
    while index <= no_nodes:
      node = self._sorted_nodes[-index] # get least loaded
      instances = node.instances.values()
      if len(instances) == 0:
        index += 1
        continue

      instances.sort(key=lambda i: i.sorting_key, reverse=True)

      i_placed = 0
      for i in instances:
        hostname = self._get_suitable_hostname(i, index)
        if hostname is None:
          continue
        to_node = self._host_dict[hostname]
        node.remove(i)
        to_node.add(i)

        self._new_state[i.id] = hostname
        i_placed += 1

      if i_placed == len(instances): no_released += 1
      index += 1

    LOG.debug('TO\n')
    LOG.debug('\n'.join([str(node) for node in self._sorted_nodes]))
    LOG.debug('\n')

    return self._new_state, no_nodes - no_released < self._no_used

