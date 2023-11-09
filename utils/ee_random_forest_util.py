"""
In this script utility functions for the random forest model are defined.
"""

import ee


def encodeRandomForest(random_forest):
    """
        This function encodes a random forest model into a feature collection.
        This is necessary because the random forest model is too large to be
        exported as a single feature collection. Therefore, it is split into
        multiple feature collections.
        
        The random forest model is encoded as a JSON string and then split into
        multiple feature collections. Each feature collection contains a maximum
        of 1000 properties. Each property contains a maximum of 100000 characters.
        These are limitations of the Earth Engine API.
            * Maximum of 100 million features
            * Maximum of 1000 properties (columns)
            * Maximum of 100,000 vertices for each row's geometry
            * Maximum of 100,000 characters per string value
        
    

    Args:
        value (value): _description_

    Returns:
        _type_: _description_
    """
    # NOTE: The following limitations are imposed by the Earth Engine API
    MAX_LENGTH = 100000
    MAX_PROPERTIES = 1000
    
    ee_string = ee.String.encodeJSON(random_forest)
    ee_stringLength = ee_string.length()
    

    def create_feature(start):
        start = ee.Number(start)
        end = start.add(MAX_LENGTH).min(ee_stringLength)
        return ee_string.slice(start, end)

    values = (
        ee.List.sequence(0, ee_stringLength, MAX_LENGTH)
        .map(create_feature)
        .filter(ee.Filter.neq("item", ""))
    )
    numberOfProperties = values.size()

    def create_feature_collection(start):
        start = ee.Number(start)
        end = start.add(MAX_PROPERTIES).min(numberOfProperties)
        propertyValues = values.slice(start, end)
        propertyKeys = ee.List.sequence(1, propertyValues.size()).map(
            lambda i: ee.Number(i).format("%d")
        )
        properties = ee.Dictionary.fromLists(propertyKeys, propertyValues)
        return ee.Feature(ee.Geometry.Point([0, 0]), properties)

    feature_collection = ee.FeatureCollection(create_feature_collection).filter(
        ee.Filter.notNull(["1"])
    )
    return feature_collection



def decodeRandomForest(random_forest):
  """Decodes a feature collection containing a decision forest.

  Args:
    feature_collection: An Earth Engine FeatureCollection.

  Returns:
    An Earth Engine FeatureCollection containing the decoded decision trees.
  """

  # Map over the feature collection to decode each feature.
  return random_forest.map(lambda feature: __decode_feature(feature))

def __decode_feature(feature):
  """Decodes a feature containing a decision tree.

  Args:
    feature: An Earth Engine Feature.

  Returns:
    An Earth Engine Feature containing the decoded decision tree.
  """

  # Get the dictionary of feature properties.
  dict = feature.toDictionary()

  # Get the keys of the dictionary, sorted by their numeric values.
  keys = dict.keys().map(lambda key: ee.Number.parse(ee.String(key))).sort()

  # Get the values of the dictionary, sorted by the keys.
  values = dict.values().sort(keys)

  # Join the values together to form a string.
  value = values.join()

  # Create a new feature with the decoded decision tree.
  return ee.Feature(None, {'value': value})