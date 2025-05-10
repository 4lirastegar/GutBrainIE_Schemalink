import json

def find_classes_with_one_dependency(dependencies_path):
    """
    Identify classes with exactly one dependency.

    Args:
        dependencies_path (str): Path to the class dependencies file.

    Returns:
        dict: Dictionary of classes with one dependency and their parent class.
    """
    with open(dependencies_path, "r") as file:
        class_dependencies = json.load(file)

    one_dependency_classes = {
        class_name: data["dependencies"][0]
        for class_name, data in class_dependencies.items()
        if len(data["dependencies"]) == 1
    }
    return one_dependency_classes

def check_parent_has_instances(parent_class, responses_path):
    """
    Check if the parent class has instances in its schemaResponse.

    Args:
        parent_class (str): The parent class name.
        responses_path (str): Path to the generated responses file.

    Returns:
        bool: True if the parent class has instances, False otherwise.
    """
    with open(responses_path, "r") as file:
        generated_responses = json.load(file)

    parent_response = generated_responses.get(parent_class, {}).get("schemaResponse", {})
    if not parent_response:
        return False

    # Check if the schemaResponse has any non-empty attribute
    for attribute, values in parent_response.items():
        if isinstance(values, list) and values:  # Non-empty list
            return True
    return False

def remove_class_and_dependents(class_name, class_dependencies, single_dependency_classes):
    """
    Recursively remove a class and its dependents from the class dependencies dictionary and single_dependency_classes.

    Args:
        class_name (str): The name of the class to remove.
        class_dependencies (dict): The dictionary of class dependencies.
        single_dependency_classes (dict): The dictionary of single dependency classes.

    Returns:
        None: The function modifies the dictionaries in place.
    """
    # Find all classes that depend on the given class
    dependents = [child for child, details in class_dependencies.items() if class_name in details.get("dependencies", [])]

    # Remove the given class from class_dependencies
    if class_name in class_dependencies:
        del class_dependencies[class_name]

    # Remove the given class from single_dependency_classes
    if class_name in single_dependency_classes:
        del single_dependency_classes[class_name]

    # Recursively remove all dependents
    for dependent in dependents:
        remove_class_and_dependents(dependent, class_dependencies, single_dependency_classes)
