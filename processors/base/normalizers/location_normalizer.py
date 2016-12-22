import jellyfish
import numpy
import distance
import pycountry
import os
import distance

from scipy.cluster.hierarchy import dendrogram, linkage, fcluster

MAX_DISTANCE = 0.9
MIN_DISTANCE = 0.01

def build_country_clusters():
    # An inner function that computs the Jaro distance between two countries
    def _cluster_distance(coord):

        # A simple cannot-link relantionship that prevents canonical clusters form being merged
        def cannot_link(coord):
            i, j = coord
            ans = False
            if countries[i] in canonical_names and countries[j] in canonical_names:
                ans = True
            return ans
        
        # A simple must-link relationship that forces merges between canonical forms and abbreviations 
        def must_link(coord):
            i, j = coord
            ans = False
            if countries[i] in acronyms:
                if len(countries[i]) == 2: 
                    ans = pycountry.countries.get(alpha_2=countries[i]).name == countries[j]
                else: 
                    ans = pycountry.countries.get(alpha_3=countries[i]).name == countries[j]
            elif countries[j] in acronyms:
                if len(countries[j]) == 2: 
                    ans = pycountry.countries.get(alpha_2=countries[j]).name == countries[i]
                else:
                    ans = pycountry.countries.get(alpha_3=countries[j]).name == countries[i]
            return ans
        
        # Setting the clustering distances according to must-link and cannot-link relationships
        if not (cannot_link(coord) or must_link(coord)):
            i, j = coord
            temp =   1 - jellyfish.jaro_distance(countries[i], countries[j])
            #temp = distance.nlevenshtein(countries[i], countries[j])
        elif cannot_link(coord):
            temp = MAX_DISTANCE
        elif must_link(coord):
            temp = MIN_DISTANCE
        return temp


    # Read an normalize country names
    training_data = open(os.path.join(os.path.dirname(__file__), 'training_sets/data for training.txt'), 'r')
    countries = [unicode(country.strip(), encoding="utf-8") for country in training_data.readlines()]

    canonical_names = []
    acronyms = []

    for c in pycountry.countries:
        canonical_names.append(c.name)
        acronyms.append(c.alpha_3)
        acronyms.append(c.alpha_2)
   
    # Compute the triangle matrix used by the hierarchical clustering
    indexes_triangle_matrix = numpy.triu_indices(len(countries), 1)
    distances_triangle_matrix = numpy.apply_along_axis(_cluster_distance, 0, indexes_triangle_matrix)

    # Compute the country likage and extract the clusters (249 is the number of acknowledged countries according to 3166-1)
    country_linkage_matrix = linkage(distances_triangle_matrix, method='complete')
    flat_custers = fcluster(country_linkage_matrix, 0.15, criterion='distance')

    clusters = {}
    for i in range(len(flat_custers)):
        clusters[flat_custers[i]] = clusters.get(flat_custers[i], []) + [countries[i]]

    return clusters

country_cluster = build_country_clusters()

def get_normalized_form(country, cluster=country_cluster):
	# Search for the country on the pre-built clusters    
    for cluster_id, cluster_items in cluster.iteritems():
        if unicode(country.strip()) in cluster_items:    
        	try:
    			# Contry found in complete cluster. Return its canonical equivalent and log the successful normalization
    			#print(cluster_items)
    			return list(set(cluster_items) & set([c.name for c in pycountry.countries]))[0]
    		except IndexError:
    			# (new) Contry found in a single cluster. Return itself and log the unsuccessful normalization
			    return country.strip()

    # Country not found. Add new location to training base before retrain the model   
    training_data = open(os.path.join(os.path.dirname(__file__), 'training_sets/data for training.txt'), 'a')
    training_data.write("%s" % country)
    training_data.close()
    return get_normalized_form(country, cluster=build_country_clusters())

# if __name__ == '__main__':
# 	#print(get_normalized_form("Venezuela"))
# 	for country in open(os.path.join(os.path.dirname(__file__), 'training_sets/data for training.txt'), 'r').readlines():
# 		print("A normalizacao de %s deu %s" %  (country.strip(), get_normalized_form(country)))