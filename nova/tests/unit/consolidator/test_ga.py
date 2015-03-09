"""
  Unit Tests for nova.consolidator.ga
"""

import mock, random
from nova import test
from nova.tests.unit.consolidator import base
from nova.consolidator.ga import core, functions, k
from nova.consolidator.ga.base import GAConsolidator

class FunctionsTestCase(test.TestCase):
  CH_LEN = 10
  POP_SIZE = functions.TournamentSelection.POP_SIZE
  MAX_VAL = 50
  MIN_VAL = -30

  def setUp(self):
    super(FunctionsTestCase, self).setUp()
    functions.TournamentSelection.P = 1 # deterministic

    # test on integer list
    self.population = []
    for i in xrange(0, self.POP_SIZE):
      chromosome = []
      for j in xrange(0, self.CH_LEN):
        chromosome.append(random.randint(self.MIN_VAL, self.MAX_VAL))
      self.population.append(chromosome)

    self.tournament = functions.TournamentSelection()
    self.roulette = functions.RouletteSelection()

    self.father = random.choice(self.population)
    self.mother = random.choice(self.population)
    self.sp_crossover = functions.SinglePointCrossover()

  def test_sp_crossover_cutpoint(self):
    child = self.sp_crossover.cross(self.father, self.mother)
    cut_point = 0
    for i, el in enumerate(child):
      if el != self.father[i]:
        cut_point = i
        break

    self.assertSequenceEqual(child[:cut_point], self.father[:cut_point])
    self.assertSequenceEqual(child[cut_point:], self.mother[cut_point:])

  def test_tournament_pool_len(self):
    expected_pool_len = int(float(self.tournament.K) / 100 * self.POP_SIZE)
    self.assertEqual(expected_pool_len, len(self.tournament._get_probs()))

  def test_roulette_pool_length_is_one(self):
    self.assertEqual(1, len(self.roulette._get_probs()))

class GACoreTestCase(base.TestCaseWithSnapshot):

  def setUp(self):
    super(GACoreTestCase, self).setUp()
    self.snapshot = self._get_snapshot(no_nodes=len(self.cns))
    core.GA.MUTATION_PROB = 1 # make mutation certain
    core.GA.ELITISM_PERC = 25 # a quarter
    self.ga_core = core.GA(self.snapshot)
    self.chromosome = self.ga_core._rnd_chromosome()

    self.all_instances = {}
    for cn in self.snapshot.nodes:
      cn_instances = cn.instances_migrable
      for i in cn_instances:
        self.all_instances[i.id] = i

    self.all_instance_ids = self.all_instances.keys()

  def test_rnd_chromo_has_all_and_only_snapshot_instances(self):
    all_instances = list(self.all_instance_ids)

    for _ in self.chromosome:
      del all_instances[0]

    self.assertTrue(len(all_instances) == 0)

  def test_chromosome_mutation(self):
    ch = self.chromosome
    before_ids = list(ch) # copy
    self.ga_core._mutate(ch)
    after_ids = ch

    #TODO find a better way to get self.assertSequenceNotEqual
    self.assertRaises(AssertionError, self.assertSequenceEqual, before_ids, after_ids)

  def test_elitism_is_applied(self):
    old_pop = self.ga_core.population
    new_pop, _ = self.ga_core._next()

    elite_len = self.ga_core.elite_len
    self.assertSequenceEqual(old_pop[:elite_len], new_pop[:elite_len])


class GAConsolidatorTestCase(base.TestCaseWithSnapshot):

  def setUp(self):
    super(GAConsolidatorTestCase, self).setUp()
    self.consolidator = GAConsolidator()
    self.snapshot = self._get_snapshot(no_nodes=len(self.cns))
    core.GA.LIMIT = 10
    core.GA.POP_SIZE = 50
    self.ga_core = core.GA(self.snapshot)

  def test_extract_migrations(self):
    old = self.snapshot
    new = self.ga_core.run()

    migs = self.consolidator._get_migrations_from_new_state(old, new)

    for m in migs:
      i_id = m.instance.id
      self.assertEqual(new[i_id], m.host.host)
      self.assertNotEqual(m.instance.host, m.host.host)