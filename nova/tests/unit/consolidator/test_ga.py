"""
  Unit Tests for nova.consolidator.ga
"""

import mock, random
from nova import test
from nova.tests.unit.consolidator import base
from nova.consolidator.ga import core, functions
from nova.consolidator.ga.base import GAConsolidator

class FunctionsTestCase(test.TestCase):
  CH_LEN = 10
  POP_SIZE = 100
  MAX_VAL = 50
  MIN_VAL = -30

  def setUp(self):
    super(FunctionsTestCase, self).setUp()

    functions.TournamentSelection.K = 25 # a quarter
    functions.TournamentSelection.P = 1 # deterministic
    functions.RouletteSelection.K = float(100) / self.POP_SIZE # adjust basing on pop_size

    # test on integer list
    self.population = []
    for i in xrange(0, self.POP_SIZE):
      chromosome = []
      for j in xrange(0, self.CH_LEN):
        chromosome.append(random.randint(self.MIN_VAL, self.MAX_VAL))
      self.population.append(chromosome)

    self.tournament = functions.TournamentSelection(self.population)
    self.roulette = functions.RouletteSelection(self.population)

    self.father = random.choice(self.population)
    self.mother = random.choice(self.population)
    self.sp_crossover = functions.SinglePointCrossover(self.father, self.mother)

  def test_sp_crossover_cutpoint(self):
    cut_point = self.sp_crossover.cut_point
    child = self.sp_crossover.cross()

    self.assertSequenceEqual(child[:cut_point], self.father[:cut_point])
    self.assertSequenceEqual(child[cut_point:], self.mother[cut_point:])

  def test_sp_crossover_null_cutpoint(self):
    cut_point = 0
    self.sp_crossover.cut_point = cut_point
    child = self.sp_crossover.cross()

    self.assertSequenceEqual(child, self.mother)

  def test_sp_crossover_max_cutpoint(self):
    cut_point = len(self.father)
    self.sp_crossover.cut_point = cut_point
    child = self.sp_crossover.cross()

    self.assertSequenceEqual(child, self.father)

  def test_tournament_pool_len(self):
    expected_pool_len = int(float(self.tournament.K) / 100 * self.POP_SIZE)
    self.assertEqual(expected_pool_len, len(self.tournament.pool_indexes))

  def test_roulette_pool_length_is_one(self):
    self.assertEqual(1, len(self.roulette.pool_indexes))

  def test_tournament_chooses_best_if_deterministic(self):
    self.assertEqual(self.population[0], self.tournament.get_chromosome())

class GACoreTestCase(base.TestCaseWithSnapshot):

  def setUp(self):
    super(GACoreTestCase, self).setUp()
    self.snapshot = self._get_snapshot(no_nodes=len(self.cns))
    core.Chromosome.MUTATION_PROB = 1 # make mutation certain
    core.GA.ELITISM_PERC = 25 # a quarter
    self.ga_core = core.GA(self.snapshot)
    self.chromosome = self.ga_core._rnd_chromo()

    self.all_instances = {}
    for cn in self.snapshot.nodes:
      cn_instances = cn.instances_running
      for i in cn_instances:
        self.all_instances[i.id] = i

    self.all_instance_ids = self.all_instances.keys()

  def _extract_instance_ids(self, ch):
    ids = []
    for g_id in ch.genes:
      insts = ch.genes[g_id].instances
      for i_id in insts:
        ids.append(i_id)
    return ids

  def test_rnd_chromo_has_all_and_only_snapshot_instances(self):
    all_instances = list(self.all_instance_ids)
    ids = self._extract_instance_ids(self.chromosome)

    for i in ids:
      all_instances.remove(i)

    self.assertTrue(len(all_instances) == 0)

  def test_chromosome_mutation(self):
    before_ids = self._extract_instance_ids(self.chromosome)
    self.chromosome.mutate()
    after_ids = self._extract_instance_ids(self.chromosome)

    self.assertItemsEqual(before_ids, after_ids)
    #TODO find a better way to get self.assertSequenceNotEqual
    self.assertRaises(AssertionError, self.assertSequenceEqual, before_ids, after_ids)

  def test_chromosome_repair(self):
    # apply crossover
    ch = self.chromosome
    another_ch = self.ga_core._rnd_chromo()

    child = self.ga_core._evolve(ch, another_ch)
    child.repair(self.all_instances)
    ids = self._extract_instance_ids(child)
    self.assertItemsEqual(ids, self.all_instance_ids)

  def test_elitism_is_applied(self):
    old_pop = self.ga_core.population
    new_pop = self.ga_core._next()

    elite_len = self.ga_core.elite_len
    self.assertSequenceEqual(old_pop[:elite_len], new_pop[:elite_len])


class GAConsolidatorTestCase(base.TestCaseWithSnapshot):

  def setUp(self):
    super(GAConsolidatorTestCase, self).setUp()
    self.consolidator = GAConsolidator()
    self.snapshot = self._get_snapshot(no_nodes=len(self.cns))
    self.ga_core = core.GA(self.snapshot)

  def test_extract_migrations(self):
    old = self.snapshot
    new = self.ga_core.run()

    migs = self.consolidator._get_migrations_from_new_state(old, new)

    i_id_host_id_mapping = {}
    for g_id in new.genes:
      partial_mapping = {i_id: g_id for i_id in new.genes[g_id].instances}
      i_id_host_id_mapping.update(partial_mapping)

    for m in migs:
      i_id = m.instance.id
      self.assertEqual(i_id_host_id_mapping[i_id], m.host.id)
      self.assertNotEqual(m.instance.host, m.host.host)