from .crossref import CrossrefProvider
from .openalex import OpenAlexProvider
from .semantic_scholar import SemanticScholarProvider
from .pubmed import PubMedProvider
from .arxiv import ArxivProvider
from .europe_pmc import EuropePMCProvider
class ScholarlyRegistry:
    def __init__(self):self._factories={'crossref':CrossrefProvider,'openalex':OpenAlexProvider,'semantic_scholar':SemanticScholarProvider,'pubmed':PubMedProvider,'arxiv':ArxivProvider,'europe_pmc':EuropePMCProvider}
    def names(self):return sorted(self._factories)
    def create(self,name,**kwargs):
        if name not in self._factories:raise KeyError(name)
        return self._factories[name](**kwargs)
    def register(self,name,factory):self._factories[name]=factory
