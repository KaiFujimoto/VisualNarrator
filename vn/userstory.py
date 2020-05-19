import json
from vn.statistics import UserStoryStatistics

class UserStory(object):
	def __init__(self, nr, text, no_punct):
		self.number = nr
		self.text = text
		self.sentence = no_punct
		self.iloc = []
		self.role = Role()
		self.means = Means()
		self.ends = Ends()
		self.indicators = []
		self.free_form = []
		self.system = WithMain()
		self.has_ends = False
		self.stats = UserStoryStatistics()

	def toJSON(self):
		if self.has_ends:
			{"number": self.number, "text": self.text, "iloc": self.iloc, "role": self.role.toJSON(), "means": self.means.toJSON(), "ends": self.ends.toJSON()}
		return {"number": self.number, "text": self.text, "iloc": self.iloc, "role": self.role.toJSON(), "means": self.means.toJSON()}

	def txtnr(self):
		return "US" + str(self.number)

	def is_func_role(self, token):
		if token.i in self.iloc:
			return True
		return False


class UserStoryPart(object):
	def __init__(self):
		self.text = []
		self.indicator = []
		self.indicator_t = ""
		self.indicator_i = -1
		self.simplified = ""

	def toJSON(self):
		return {"text": str(self.text), "indicator": str(self.indicator)}

class FreeFormUSPart(UserStoryPart):
	def __init__(self):
		self.simplified = ""
		self.main_verb = WithPhrase()
		self.main_object = WithPhrase()
		self.free_form = []
		self.verbs = []
		self.phrasal_verbs = []
		self.nouns = []
		self.proper_nouns = []
		self.noun_phrases = []
		self.compounds = []
		self.subject = WithPhrase()

class Role(UserStoryPart):
	def __init__(self):
		self.functional_role = WithPhrase()

class Means(FreeFormUSPart):
	pass

class Ends(FreeFormUSPart):
	pass

class WithMain(object):
	def __init__(self):
		self.main = []

class WithPhrase(WithMain):
	def __init__(self):
		self.phrase = []
		self.compound = []
		self.type = ""
