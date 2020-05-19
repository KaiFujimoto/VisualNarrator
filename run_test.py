#!/usr/bin/env python

import sys
import string
import os.path
import timeit
import pkg_resources

from argparse import ArgumentParser
import spacy
import en_core_web_md
from jinja2 import FileSystemLoader, Environment, PackageLoader

from vn.io import Reader, Writer
from vn.miner import StoryMiner
from vn.matrix import Matrix
from vn.userstory import UserStory
from vn.utility import Printer, multiline, remove_punct, t, is_i, tab, is_comment, occurence_list, is_us
from vn.pattern import Constructor
from vn.statistics import Statistics, Counter


def initialize_nlp():
	# Initialize spaCy just once (this takes most of the time...)
	print("Initializing Natural Language Processor. . .")
	nlp = en_core_web_md.load()
	return nlp

def main(filename, systemname, print_us, print_ont, statistics, link, prolog, json, per_role, threshold, base, weights, spacy_nlp):

	"""General class to run the entire program
	"""

	start_nlp_time = timeit.default_timer()
	nlp = spacy_nlp
	nlp_time = timeit.default_timer() - start_nlp_time

	start_parse_time = timeit.default_timer()
	miner = StoryMiner()

	# Read the input file
	set = Reader.parse(filename)
	us_id = 1

	# Keep track of all errors
	success = 0
	fail = 0
	list_of_fails = []
	errors = ""
	c = Counter()

	# Keeps track of all succesfully created User Stories objects
	us_instances = []
	failed_stories = []
	success_stories = []

	# Parse every user story (remove punctuation and mine)
	for s in set:
		try:
			user_story = parse(s, us_id, systemname, nlp, miner)
			user_story = c.count(user_story)
			success = success + 1
			us_instances.append(user_story)
			success_stories.append(s)
		except ValueError as err:
			failed_stories.append([us_id, s, err.args])
			errors += "\n[User Story " + str(us_id) + " ERROR] " + str(err.args[0]) + "! (\"" + " ".join(str.split(s)) + "\")"
			fail = fail + 1
		us_id = us_id + 1

	# Print errors (if found)
	if errors:
		Printer.print_head("PARSING ERRORS")
		print(errors)

	parse_time = timeit.default_timer() - start_parse_time

	# Generate the term-by-user story matrix (m), and additional data in two other matrices
	start_matr_time = timeit.default_timer()

	matrix = Matrix(base, weights)
	matrices = matrix.generate(us_instances, ' '.join([u.sentence for u in us_instances]), nlp)
	m, count_matrix, stories_list, rme = matrices

	matr_time = timeit.default_timer() - start_matr_time

	# Generate the ontology
	start_gen_time = timeit.default_timer()

	patterns = Constructor(nlp, us_instances, m)
	out = patterns.make(systemname, threshold, link)
	output_ontology, output_prolog, output_ontobj, output_prologobj, onto_per_role = out

	all_classes_list = []
	i = 0
	for class_vn in output_ontobj.classes:
		one_concept = {'id': i, 'class_name': class_vn.name, 'parent_name': class_vn.parent,
                       'occurs_in': occurence_list(class_vn.stories), 'weight': '0', 'group': class_vn.is_role}
		all_classes_list.append(one_concept)
		i += 1
	nodes = [{"id": cl["id"], "label": cl["class_name"], "weight": cl["weight"]} for cl in all_classes_list]
	relationships_query = output_prologobj.relationships

	all_relationships_list = []
	for relationship in relationships_query:
		one_concept = {'relationship_domain': relationship.domain, 'relationship_name': relationship.name, 'relationship_range': relationship.range}
		all_relationships_list.append(one_concept)

	edges_id_list = []
	concepts_query = []
	concepts_dict = {}
	concepts_dict_list = []
	relationshipslist = []
	i = 0
	for class_vn in all_classes_list:

		one_concept = {'class_id': i, 'class_name': class_vn['class_name'], 'parent_name': class_vn['parent_name'], 'weight': '0', 'group': class_vn['group']}
		concepts_query.append(one_concept)
		i += 1
	for concept in concepts_query:
		# print(concept)
		concepts_dict[concept['class_id']] = concept['class_name']
		concepts_dict_list.append([concept['class_id'], concept['class_name']])
	i = 0
	for rel in all_relationships_list: #app.py 868
		# print(rel)
		relationshipslist.append([rel['relationship_domain'], rel['relationship_range'], rel['relationship_name']])
		for concept in concepts_dict_list:
			if rel['relationship_domain'] == concept[1]:
				x = concept[0]

		for concept in concepts_dict_list:
			if rel['relationship_range'] == concept[1]:
				y = concept[0]

		if rel['relationship_name'] == 'isa':
			edges_id_dict = {'from': x, 'to': y, 'label': rel['relationship_name'], 'dashes': "true"}
		else:
			edges_id_dict = {'from': x, 'to': y, 'label': rel['relationship_name']}
		i += 1
        # ELSE??
		edges_id_list.append(edges_id_dict)

	print({'nodes': nodes, 'edges': edges_id_list})
	return({'nodes': nodes, 'edges': edges_id_list})

	# Print out the ontology in the terminal, if argument '-o'/'--print_ont' is chosen


def parse(text, id, systemname, nlp, miner):
	"""Create a new user story object and mines it to map all data in the user story text to a predefined model

	:param text: The user story text
	:param id: The user story ID, which can later be used to identify the user story
	:param systemname: Name of the system this user story belongs to
	:param nlp: Natural Language Processor (spaCy)
	:param miner: instance of class Miner
	:returns: A new user story object
	"""
	no_punct = remove_punct(text)
	no_double_space = ' '.join(no_punct.split())
	doc = nlp(no_double_space)
	user_story = UserStory(id, text, no_double_space)
	user_story.system.main = nlp(systemname)[0]
	user_story.data = doc
	#Printer.print_dependencies(user_story)
	#Printer.print_noun_phrases(user_story)
	miner.structure(user_story)
	user_story.old_data = user_story.data
	user_story.data = nlp(user_story.sentence)
	miner.mine(user_story, nlp)
	return user_story

def generate_report(report_dict):
	"""Generates a report using Jinja2

	:param report_dict: Dictionary containing all variables used in the report
	:returns: HTML page
	"""
	CURR_DIR = os.path.dirname(os.path.abspath(__file__))

	loader = FileSystemLoader( searchpath=str(CURR_DIR) + "/templates/" )
	env = Environment( loader=loader, trim_blocks=True, lstrip_blocks=True )
	env.globals['text'] = t
	env.globals['is_i'] = is_i
	env.globals['apply_tab'] = tab
	env.globals['is_comment'] = is_comment
	env.globals['occurence_list'] = occurence_list
	env.tests['is_us'] = is_us
	template = env.get_template("report.html")

	return template.render(report_dict)


def call(filename, spacy_nlp):
	args2 = program("--return-args")
	weights = [args2.weight_func_role, args2.weight_main_obj, args2.weight_ff_means, args2.weight_ff_ends,
			   args2.weight_compound]
	filename = open(filename)
	return main(filename, args2.system_name, args2.print_us, args2.print_ont, args2.statistics, args2.link, args2.prolog,
				args2.json, args2.per_role, args2.threshold, args2.base_weight, weights, spacy_nlp)


def program(*args):
	p = ArgumentParser(
		usage='''run.py <INPUT FILE> [<args>]

///////////////////////////////////////////
//              Visual Narrator          //
///////////////////////////////////////////

This program has multiple functionalities:
    (1) Mine user story information
    (2) Generate an ontology from a user story set
    (3) Generate Prolog from a user story set (including links to 'role', 'means' and 'ends')
    (4) Get statistics for a user story set
''',
		epilog='''{*} Utrecht University.
			M.J. Robeer, 2015-2017''')

	if "--return-args" not in args:
		p.add_argument("filename",
                     help="input file with user stories", metavar="INPUT FILE",
                     type=lambda x: is_valid_file(p, x))
	p.add_argument('--version', action='version', version='Visual Narrator v0.9 BETA by M.J. Robeer')

	g_p = p.add_argument_group("general arguments (optional)")
	g_p.add_argument("-n", "--name", dest="system_name", help="your system name, as used in ontology and output file(s) generation", required=False)
	g_p.add_argument("-u", "--print_us", dest="print_us", help="print data per user story in the console", action="store_true", default=False)
	g_p.add_argument("-o", "--print_ont", dest="print_ont", help="print ontology in the console", action="store_true", default=False)
	g_p.add_argument("-l", "--link", dest="link", help="link ontology classes to user story they originate from", action="store_true", default=False)
	g_p.add_argument("--prolog", dest="prolog", help="generate prolog output (.pl)", action="store_true", default=False)
	g_p.add_argument("--return-args", dest="return_args", help="return arguments instead of call VN", action="store_true", default=False)
	g_p.add_argument("--json", dest="json", help="export user stories as json (.json)", action="store_true", default=False)

	s_p = p.add_argument_group("statistics arguments (optional)")
	s_p.add_argument("-s", "--statistics", dest="statistics", help="show user story set statistics and output these to a .csv file", action="store_true", default=False)

	w_p = p.add_argument_group("conceptual model generation tuning (optional)")
	w_p.add_argument("-p", "--per_role", dest="per_role", help="create an additional conceptual model per role", action="store_true", default=False)
	w_p.add_argument("-t", dest="threshold", help="set threshold for conceptual model generation (INT, default = 1.0)", type=float, default=1.0)
	w_p.add_argument("-b", dest="base_weight", help="set the base weight (INT, default = 1)", type=int, default=1)
	w_p.add_argument("-wfr", dest="weight_func_role", help="weight of functional role (FLOAT, default = 1.0)", type=float, default=1)
	w_p.add_argument("-wdo", dest="weight_main_obj", help="weight of main object (FLOAT, default = 1.0)", type=float, default=1)
	w_p.add_argument("-wffm", dest="weight_ff_means", help="weight of noun in free form means (FLOAT, default = 0.7)", type=float, default=0.7)
	w_p.add_argument("-wffe", dest="weight_ff_ends", help="weight of noun in free form ends (FLOAT, default = 0.5)", type=float, default=0.5)
	w_p.add_argument("-wcompound", dest="weight_compound", help="weight of nouns in compound compared to head (FLOAT, default = 0.66)", type=float, default=0.66)

	if (len(args) < 1):
		args = p.parse_args()
	else:
		args = p.parse_args(args)

	weights = [args.weight_func_role, args.weight_main_obj, args.weight_ff_means, args.weight_ff_ends, args.weight_compound]

	if not args.system_name or args.system_name == '':
		args.system_name = "System"
	if not args.return_args:
		spacy_nlp = initialize_nlp()
		return main(args.filename, args.system_name, args.print_us, args.print_ont, args.statistics, args.link, args.prolog, args.json, args.per_role, args.threshold, args.base_weight, weights, spacy_nlp)
	else:
		return args

def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("Could not find file " + str(arg) + "!")
    else:
        return open(arg, 'r')

if __name__ == "__main__":
	program()
