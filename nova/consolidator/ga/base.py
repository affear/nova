from nova.consolidator.base import BaseConsolidator
from nova.consolidator.ga.core import GA
from oslo_log import log as logging
from nova.i18n import _LI

LOG = logging.getLogger(__name__)

class GAConsolidator(BaseConsolidator):

  def _get_migrations_from_new_state(self, snapshot, new_state):
    migs = []
    i_mapping = {i.id: i for i in snapshot.instances_migrable}
    h_mapping = {h.host: h for h in snapshot.nodes}
    old_i_id_hostname = {i.id: i.host for i in snapshot.instances_migrable}
    new_i_id_hostname = {}
    for hostname in new_state:
      for i_id in new_state[hostname]:
        new_i_id_hostname[i_id] = hostname

    for i_id in new_i_id_hostname:
      old_hostname = old_i_id_hostname[i_id]
      new_hostname = new_i_id_hostname[i_id]
      if new_hostname != old_hostname:
        new_host = h_mapping[new_hostname]
        instance = i_mapping[i_id]
        new_mig = self.Migration(instance, new_host)
        migs.append(new_mig)

    return migs


  def get_migrations(self, snapshot):
    no_nodes = len(snapshot.nodes)
    no_inst = len(snapshot.instances_migrable)

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