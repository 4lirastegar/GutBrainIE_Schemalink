import json

# File path to class_dependencies.json

def find_classes_with_two_dependencies(dependencies_path):
    """
    Identify classes with exactly two dependencies.

    Args:
        dependencies_path (str): Path to the class dependencies file.

    Returns:
        dict: Dictionary of classes with two dependencies and their parent classes.
    """
    with open(dependencies_path, "r") as file:
        class_dependencies = json.load(file)

    two_dependency_classes = {
        class_name: data["dependencies"]
        for class_name, data in class_dependencies.items()
        if len(data["dependencies"]) == 2
    }
    print("Classes with exactly two dependencies:")
    print(two_dependency_classes)
    return two_dependency_classes

def remove_class_and_dependents(class_name, class_dependencies, two_dependency_classes):
    """
    Recursively remove a class and its dependents from the class dependencies dictionary and two_dependency_classes.

    Args:
        class_name (str): The name of the class to remove.
        class_dependencies (dict): The dictionary of class dependencies.
        two_dependency_classes (dict): The dictionary of two dependency classes.

    Returns:
        None: The function modifies the dictionaries in place.
    """
    # Find all classes that depend on the given class
    dependents = [child for child, deps in class_dependencies.items() if class_name in deps.get("dependencies", [])]

    # Remove the given class from class_dependencies
    if class_name in class_dependencies:
        del class_dependencies[class_name]

    # Remove the given class from two_dependency_classes
    if class_name in two_dependency_classes:
        del two_dependency_classes[class_name]

    # Recursively remove all dependents
    for dependent in dependents:
        remove_class_and_dependents(dependent, class_dependencies, two_dependency_classes)

def check_and_remove_two_dependency_classes(two_dependency_classes, responses_path, class_dependencies_file):
    """
    Check if the dependent classes of classes with two dependencies have instances.
    If not, remove those classes and their dependents.

    Args:
        two_dependency_classes (dict): Classes with two dependencies and their parent classes.
        responses_path (str): Path to the generated responses file.
        class_dependencies_file (str): Path to the class dependencies file.

    Returns:
        None: Modifies the dependencies file in place.
    """
    # Load generated responses and class dependencies
    with open(responses_path, "r") as file:
        generated_responses = json.load(file)

    with open(class_dependencies_file, "r") as file:
        class_dependencies = json.load(file)

    for class_name, dependencies in two_dependency_classes.copy().items():
        # Check if both dependencies have instances
        dependency_instances = {
            dep: any(
                values for values in generated_responses.get(dep, {}).get("schemaResponse", {}).values()
                if isinstance(values, list) and values
            )
            for dep in dependencies
        }

        # If any dependency is missing instances, remove the class and its dependents
        if not all(dependency_instances.values()):
            print(f"Class '{class_name}' has dependencies with missing instances. Removing '{class_name}' and its dependents.")
            for dep, has_instances in dependency_instances.items():
                if not has_instances:
                    print(f"Dependency '{dep}' has no instances. Removing it and its dependents.")
                    remove_class_and_dependents(dep, class_dependencies, two_dependency_classes)
            remove_class_and_dependents(class_name, class_dependencies, two_dependency_classes)

    # Save the updated dependencies back to the file
    with open(class_dependencies_file, "w") as file:
        json.dump(class_dependencies, file, indent=4)

    print("Updated class dependencies saved.")

# Example usage
