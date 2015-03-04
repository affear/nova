from nova.consolidator.base import BaseConsolidator
from nova.consolidator.ga.core import GA

class GAConsolidator(BaseConsolidator):

  def _get_migrations_from_new_state(self, snapshot, new_state):
    migs = []

    i_id_host_id_mapping = {}
    for g_id in new_state.genes:
      partial_mapping = {i_id: g_id for i_id in new_state.genes[g_id].instances}
      i_id_host_id_mapping.update(partial_mapping)

    hostname_id_mapping = {cn.host: cn.id for cn in snapshot.nodes}
    id_host_mapping = {cn.id: cn for cn in snapshot.nodes}

    for instance in snapshot.instances_running:
      i_id = instance.id
      old_host_id = hostname_id_mapping[instance.host]
      new_host_id = i_id_host_id_mapping[i_id]
      if new_host_id != old_host_id:
        new_host = id_host_mapping[new_host_id]
        new_mig = self.Migration(instance, new_host)
        migs.append(new_mig)

    return migs


  def get_migrations(self, snapshot):
    no_nodes = len(snapshot.nodes)
    no_inst = len(snapshot.instances_running)

    if no_inst == 0:
      LOG.info(_LI('No running instance found. Cannot migrate.'))
      return []

    if no_nodes == 0:
      LOG.info(_LI('No compute node in current snapshot'))
      return []

    if no_nodes == 1:
      LOG.info(_LI('Only one compute node in current snapshot. Cannot migrate.'))
      return []
    
    # ok, let's go
    ga = GA(snapshot)
    new_state = ga.run()

    return self._get_migrations_from_new_state(snapshot, new_state)