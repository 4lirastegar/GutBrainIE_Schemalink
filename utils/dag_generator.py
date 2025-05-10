import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors



def draw_dependency_graph(json_file, output_image="dependency_graph.png"):
    """
    Draw an unlabeled dependency graph for prompts, based on the final JSON file.

    Args:
        json_file (str): Path to the final prompts JSON file.
        output_image (str): Path to save the generated graph image.
    """
    # Load the JSON data
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # Create a directed graph
    G = nx.DiGraph()

    # Add nodes and edges
    for class_name, details in data.items():
        # Add the node for the current class with "Prompt" suffix
        node_name = f"{class_name}Prompt"
        G.add_node(node_name, layer=1, color="green")  # Default color for independent classes

        # If the class has dependencies, add edges
        dependencies = details.get("dependencies", {})
        if isinstance(dependencies, dict):
            for dep_class in dependencies.values():
                dep_node_name = f"{dep_class}Prompt"
                G.add_edge(dep_node_name, node_name)
                G.nodes[node_name]["layer"] = 2  # Mark dependent nodes in the second layer
                G.nodes[node_name]["color"] = "#ADD8E6" 
        elif isinstance(dependencies, list):
            for dep_class in dependencies:
                dep_node_name = f"{dep_class}Prompt"
                G.add_edge(dep_node_name, node_name)
                G.nodes[node_name]["layer"] = 2
                G.nodes[node_name]["color"] = "#ADD8E6" 

    # Get node colors and positions
    node_colors = [G.nodes[node]["color"] for node in G.nodes()]
    pos = nx.multipartite_layout(G, subset_key="layer")  # Position nodes by layer

    # Draw the graph
    plt.figure(figsize=(12, 8))
    nx.draw(
        G, pos, with_labels=True, labels={node: node for node in G.nodes()},  # Add node names with "Prompt" suffix
        node_color=node_colors, node_size=3000, font_size=10, font_weight="bold",
        arrowsize=20, edge_color="black"
    )
    
    plt.title("Dependency Graph (Unlabeled)", fontsize=16)
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    plt.show()


# Example Usage
# draw_dependency_graph_v2("generated_prompts/final_prompts.json", "dependency_graph_v2.png")


# Example Usage
