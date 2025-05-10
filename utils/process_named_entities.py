import json
from openai import OpenAI

# PLACE API KEY HERE
# Initialize OpenAI client

API_KEY=""
client = OpenAI(api_key=API_KEY)

def convert_extracted_to_span_annotated(output_responses_path, text_sample_path, final_output_path, pmid="00000000"):
    import json
    from collections import defaultdict

    def find_all_occurrences(text, substring):
        """Return all start indices of substring in text."""
        start = 0
        indices = []
        while True:
            start = text.find(substring, start)
            if start == -1:
                break
            indices.append(start)
            start += len(substring)
        return indices

    # Load extracted mentions from GPT output
    with open(output_responses_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Load text
    with open(text_sample_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # Extract title and abstract
    title_start = full_text.find("title:")
    abstract_start = full_text.find("abstract:")

    title = full_text[title_start + len("title:"):abstract_start].strip().strip('"').strip()
    abstract = full_text[abstract_start + len("abstract:"):].strip().strip('"').strip()

    # Define mapping from internal class names to final labels
    class_name_to_label = {
        "AnatomicalLocation": "anatomical location",
        "Animal": "animal",
        "BiomedicalTechnique": "biomedical technique",
        "Bacteria": "bacteria",
        "Chemical": "chemical",
        "DietarySupplement": "dietary supplement",
        "DiseaseDisorderOrFinding": "DDF",
        "Metabolites": "chemical",
        "Drug": "drug",
        "Food": "food",
        "Gene": "gene",
        "Human": "human",
        "Microbiome": "microbiome",
        "StatisticalTechnique": "statistical technique",
    }

    entities = []

    for class_name, content in data.items():
        if not content or "schemaResponse" not in content or "mentions" not in content["schemaResponse"]:
            continue

        mentions = content["schemaResponse"]["mentions"]
        label = class_name_to_label.get(class_name, class_name)

        for span in mentions:
            found = False

            title_positions = find_all_occurrences(title, span)
            for start_idx in title_positions:
                entity = {
                    "start_idx": start_idx,
                    "end_idx": start_idx + len(span) - 1,
                    "location": "title",
                    "text_span": span,
                    "label": label
                }
                entities.append(entity)
                found = True

            abstract_positions = find_all_occurrences(abstract, span)
            for start_idx in abstract_positions:
                entity = {
                    "start_idx": start_idx,
                    "end_idx": start_idx + len(span) - 1,
                    "location": "abstract",
                    "text_span": span,
                    "label": label
                }
                entities.append(entity)
                found = True

            if not found:
                print(f"⚠️ Could not find span: '{span}'")

    # Output in BioNLP required format
    output = {pmid: {"entities": entities}}

    with open(final_output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=True)

    print(f"✅ Final span-based entity output saved to {final_output_path}")






def process_named_entity_classes(
    named_entity_classes, schema_path, text_sample_path, response_formats_path, output_responses_path, prompts_save_path
):
    """
    Generate prompts, call GPT for named entity extraction, and save results.

    Args:
        named_entity_classes (dict): Named entity classes to process.
        schema_path (str): Path to the schema JSON file.
        text_sample_path (str): Path to the input text sample file.
        response_formats_path (str): Path to the response formats JSON file.
        output_responses_path (str): Path to save the extracted responses.
        prompts_save_path (str): Path to save the generated prompts.

    Returns:
        None: Saves generated responses and prompts to their respective files.
    """




    # Load schema and text
    with open(schema_path, "r") as file:
        schema = json.load(file)

    with open(text_sample_path, "r", encoding='utf-8') as file:
        text = file.read()
    # Ensure consistent Unicode handling
    #text = text.encode('utf-8').decode('unicode-escape')
    print(text)
    # text_safe = text.encode("unicode_escape").decode("utf-8").replace("{", "{{").replace("}", "}}")
    # text = text.encode("utf-8").decode("unicode_escape")
    # Load response formats
    with open(response_formats_path, "r") as schema_file:
        response_formats = json.load(schema_file)

    combined_responses = {}
    generated_prompts = {}
    already_extracted_entities = []  # List of tuples (entity_text, label)


    # Extract schema title and description
    schema_title = schema.get("title", "")
    schema_description = schema.get("description", "")
    schema_intro = (
        f"The schema is titled '{schema_title}' and described as follows: {schema_description}"
        if schema_title and schema_description
        else f"the schema is described as follows: {schema_description}"
        if schema_description
        else f"The schema is titled '{schema_title}'"
        if schema_title
        else ""
    )

    # Process each named entity class
    for class_name, details in named_entity_classes.items():
        class_info = schema["classes"].get(class_name, {})
        class_description = class_info.get("description", "")
        # attributes = class_info.get("attributes", {})


        # Generate schema and attribute prompts
        class_intro = f"A '{class_name}' is defined as: {class_description}. " if class_description else ""
        print(class_intro)
        # Extract optional examples and rules
        annotations = class_info.get("annotations", {})
        prompt_examples = annotations.get("prompt.examples")
        annotation_rules = annotations.get("annotation_rules")
        example_input=annotations.get("example.input")
        example_output=annotations.get("example.output")

        # Build schema prompt
        schema_prompt = (
            f"Extract all mentions of entities of class '{class_name}' that are **explicitly** mentioned in the provided text. "
            f"{class_intro} Return a list of all entity mentions for the class {class_name}."
        )

        # Add optional sections
        if prompt_examples:
            schema_prompt += f"""

            # Examples  

            # {prompt_examples}"""

        # If there are already extracted entities, add a warning
        # if already_extracted_entities:
        #     previous_entities_text = "\n".join([f"- {text_span} → {label}" for text_span, label in already_extracted_entities])
        #     schema_prompt = f"""⚡ IMPORTANT CONTEXT ⚡
        # The following entities have already been extracted with their respective classes:
        # {previous_entities_text}

        # ❗ DO NOT annotate these entities again under '{class_name}' or any other class.

        # """ + schema_prompt




        # Extract response formats
        schema_response_format = response_formats.get(class_name, {}).get("schemaResponseFormat")
        # attribute_response_format = response_formats.get(class_name, {}).get("attributeResponseFormat")

        combined_responses[class_name] = {"schemaResponse": None}
        extracted_labels = []

        instructions = f"""
        Your task is to extract mentions of type '{class_name}' from the provided biomedical text. Rules are:
        - Annotate only full, standalone words or word groups. Do NOT extract partial words.
        - Composite names (e.g., "short-chain fatty acids") must be labeled as one entity if meaningful.
        - Always extract the **longest valid version** of a mention, including important modifiers.
        - Do NOT include punctuation at the start/end. Internal punctuation (like hyphens) is allowed.
        - Avoid overlapping mentions. Each span must be independent.

        ### Abbreviations
        - Extract both full names **and** abbreviations when they appear together:  
          e.g., `Prostaglandin E2 (PGE2)` → "Prostaglandin E2" and "PGE2"
        - Also extract **standalone abbreviations** if they clearly refer to known biomedical terms, **even when the full form is NOT present**:  
          e.g., "AD", "MDD", "PD", "HC"

        ### Do NOT Extract
        - Generic terms alone (e.g., “disease”, “patients”).
        - Morphological variants like adjectives ("hypertensive").
        - Mentions that overlap with previously extracted spans.
        """

        if annotation_rules:
            instructions += f"""
            * {annotation_rules}
        """
            
        print("===== SYSTEM PROMPT =====")
        print(f"""
            # Identity

            You are an expert biomedical annotator working on structured entity extraction.

            # Instructions

            {instructions}

            # Schema

            {schema_prompt}
            """)

        # Call GPT for schema response
        if schema_response_format:
            print(schema_response_format["json_schema"])
            try:
                schema_response = client.chat.completions.create(
                    model="gpt-4o-2024-08-06",
                    messages = [
                      {
                          "role": "system",
                          "content": f"""
                  
                  # Identity

                  You are an expert biomedical annotator working on structured entity extraction.

                  # Instructions

                  {instructions}

                  # Schema

                  {schema_prompt}
                  """
                      },
                      {
                          "role": "user",
                          "content": f"""
                        
                          Extract mentions from the following input:
                          "{text}"

                         # Examples

                        Example Input 1:
                         {example_input}
                        Example Output 1:
                         {example_output}

                        Example Input 2:
                        "The aggregation of gamma-synuclein (γsyn) in the brain is a hallmark of Parkinson’s disease."

                        Example Output 2:
                        {{
                          "Gene": {{
                            "schemaResponse": {{
                              "mentions": [
                                "gamma-synuclein",
                                "γsyn"
                              ]
                            }}
                          }}
                        }}
                          """
                      }
                  ],
                    response_format={"type": "json_schema", "json_schema": schema_response_format["json_schema"]}
                )
                schema_response_json = json.loads(schema_response.choices[0].message.content)
                combined_responses[class_name]["schemaResponse"] = schema_response_json
                extracted_labels = list(schema_response_json.values())[0] if schema_response_json else []
                # Save the extracted labels to the already_extracted_entities list
                for label_text in extracted_labels:
                    already_extracted_entities.append((label_text, class_name))

                print(f"✅ Entities extraction completed for {class_name}")
            except Exception as e:
                print(f"❌ Error processing schema prompt for {class_name}: {e}")




            generated_prompts[class_name] = {"schema_prompt": schema_prompt}
        
    # Save responses and prompts
# When saving responses, ensure proper Unicode handling
    with open(output_responses_path, "w") as output_file:
        json.dump(combined_responses, output_file, indent=4)
    print(f"📁 Responses saved to {output_responses_path}.")

    with open(prompts_save_path, "w") as prompts_file:
        json.dump(generated_prompts, prompts_file, indent=4)
    print(f"📁 Prompts saved to {prompts_save_path}.")


    convert_extracted_to_span_annotated(
      output_responses_path="output/generated_responses.json",
      text_sample_path=text_sample_path,
      final_output_path="converted_entities_with_spans.json"
    )

