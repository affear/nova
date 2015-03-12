from nova.tests.unit.consolidator import base
from nova.consolidator.holistic import core
from nova.consolidator.holistic.base import HolisticConsolidator

class HolisticTestCase(base.TestCaseWithSnapshot):

  def setUp(self):
    super(HolisticTestCase, self).setUp()
    self.snapshot = self._get_snapshot(no_nodes=len(self.cns))
    self.holi_core = core.Holistic(self.snapshot)
    self.holi_cons = HolisticConsolidator()

  def test_extract_migrations(self):
    old = self.snapshot
    new, _ = self.holi_core.run()

    migs = self.holi_cons._get_migrations_from_new_state(old, new)

    for m in migs:
      i_id = m.instance.id
      self.assertEqual(new[i_id], m.host.host)
      self.assertNotEqual(m.instance.host, m.host.host)