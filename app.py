from flask import Flask, render_template, request, redirect, url_for
import marqo
from transformers import AutoTokenizer, logging
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Any
import guidance
import json


# Set up the model
model_id = "TheBloke/LlongOrca-7B-16K-GPTQ"
model_basename = "model"
tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
device = "cuda:0"
model = AutoGPTQForCausalLM.from_quantized(model_id,
                                           model_basename=model_basename,
                                           use_safetensors=True,
                                           trust_remote_code=True,
                                           use_triton=False,
                                           device=device,
                                           quantize_config=None)

llm = guidance.llms.Transformers(model, tokenizer,device=device, temperature=1)

print(model_id + " loaded.")

# boot vector search

# mq = marqo.Client(url='http://localhost:8882')
# mq.index("events").delete()

# try:
#     mq.create_index("events", model="hf/all_datasets_v4_MiniLM-L6")
# except:
#     pass

app = Flask(__name__)

global_game_state = {}

@app.route('/')
def main():
    return redirect(url_for('generate_state'))



@app.route('/state')
def generate_state():

    global global_game_state_v2
    global state_evaluation
    global global_storyline

    guidance.llms.Transformers.cache.clear()

    global_game_state_v2 = {'''### Assets (a list of assets owned by the player)
    Gold: 20k in cash, 40k in crypto
    House.Location: Utrecht
    Loans: 40k study financing debt
    Company: YOM

    ### Relations (a list of relations between the player and other agents)
    Wife: 80
    Wife.Friendly: 60
    Wife.Love: 90
    Banijay.AcquisitionInterest: 70

    ### Conditions (a list of conditions that characterize the player)
    Age: 31 years
    Married: Yami de Moel
    Personality: INTP
    Nationality: Dutch

    ### World State (an overview of past events that were meaningful to the player)
    Banijay: condering to acquire metaverse streaming company YOM
    YOM: recently went bankrupt'''}

    global_storyline = {'''### Storyline Title
    None

    ### Thematic closure conditions
    None

    ### Storyline Narrative
    None

    ### Parameter Focus
    None
    '''}

    next_step = ["new storyline", "event for an existing storyline"]


    evaluator = guidance("""{{global_game_state_v2}}\n{{global_storyline}}\n
    ### Instruction

    Evaluate game state and storylines on:
    1. Complexity: a very complex or paradoxical state might warrant a new storyline to resolve some of that complexity, while a complex or urgent storyline might warrant a new event to resolve some of that complexity. High complexity is likely to generate events more frequently. 
    2. Significance/Urgency: some parts of the state or some storyline are deemed more significant or require more urgent attention than other parts of the state.
    3. Changes: large jumps in state changes may warrant implicit complexity and therefore can trigger new storylines. Changes in storylines may lead to thematic closure - ending the storyline.
    Based on the evaluation, determine if to create a new event for an existing storyline or to create a new storyline altogether.

    Output as:

    ### Game State Complexity
    {{gen 'Evaluate level of complexity of the game state' temperature=1 max_tokens=100}}

    ### Game State Significance
    {{gen 'Evaluate significance of elements of the game state' temperature=1 max_tokens=100}}
                         
    ### Game State Changes
    {{gen 'Evaluate recent jumps in game state changes' temperature=1 max_tokens=100}}

    ### Storyline Complexity
    {{gen 'Evaluate level of complexity of the existing storyline' temperature=1 max_tokens=100}}                   

    ### Storyline Urgency
    {{gen 'Evaluate level of urgency of the existing storyline' temperature=1 max_tokens=100}}

    ### Storyline Changes
    {{gen 'Evaluate the thematic closure of the existing storyline' temperature=1 max_tokens=100}}

    ### Judgement
    {{gen 'Determine if to create a new event for an existing storyline or to create a new storyline altogether' temperature=1 max_tokens=100}}

    ### Conclusion
    'Create a {{select 'Type' options=next_step}}'""")

    output = evaluator(
        global_game_state_v2=str(global_game_state_v2),
        global_storyline=str(global_storyline),
        next_step=next_step,
        llm=llm
    )

    return render_template('state.html', output=output)

    # parse the event into a data model
    print(output)

@app.route('/event', methods=['GET', 'POST'])
def show_event():
    # Example of how to fetch an event from Marqo based on the query
    
    global global_game_state

    if request.method == 'GET':
        event = {
            "LatestEvents": "",
            "NewStory": "You are the prince of the Netherlands. You grew up in a palace in the Hague. You are the son of the king and queen.",
            "OldStory": "",
            "EventBody": "You received a message from the emperor of France. He wants to marry his daughter to you.",
            "Title": "Royal Marriage",
            "Impact": "Medium",
            "PossibleActions": ["Accept", "Decline", "Ask for money"],
            "ChosenAction": "",
            "Entities": ["France", "Netherlands"],
            "Type": "Diplomatic",
            "_id": "1",
        }
        
        global_game_state['event'] = event


    elif request.method == 'POST':
        class Event(BaseModel):
            LatestEvents: str = Field(description="The events that led to the current moment")
            NewStory: str = Field(description="The story that led to the current event")
            OldStory: str = Field(description="The story that led to the previous event")
            EventBody: str = Field(description="Textual description or a generative script")
            Title: str = Field(description="A short, descriptive title for the event")
            Impact: str = Field(description="The impact of the event on the player (e.g., low, medium, high)")
            PossibleActions: List[str] = Field(description="List of player actions the event offers")
            ChosenAction: str = Field(description="The action the player chose")
            Entities: List[str] = Field(description="List of entities (players, dynasties, countries) affected by the event")
            Type: str = Field(description="Class of event (e.g., diplomatic, economic, etc.)")
            Id: str = Field(description="Unique identifier for the event", alias="_id")
        
        parser = PydanticOutputParser(pydantic_object=Event)

        print("Data model loaded.")

        query = request.form['action']
        event = global_game_state.get('event', {})

        event |= {'ChosenAction': query}
        event = json.dumps(event)
        print(event)
        event = parser.parse(event).dict(by_alias=True)

        # add the event to a list of events
        event_list = []
        event_list.append(event)
        print(event_list)
        mq.index("events").add_documents(event_list, tensor_fields=["Title", "EventBody", "ChosenAction"])


        # Replace the query with the selected action
        # Perform additional logic here, like updating the database


        # Set up a guidance template
        mq.index("events").refresh()

        guidance.llms.Transformers.cache.clear()

        interaction_types = ["Diplomatic", "Economic", "Military", "Religious", "Dynastic", "Cultural", "Natural", "Other"]
        impact_scores = ["Low", "Medium", "High"]

        JSON_builder = guidance("""{{#block hidden=True}}Act as an expert scenerio writer and game master for grand strategy games. You know how to craft engaging stories that align with context and player actions, structured as JSON events. Write the EventBody in the 2nd person as if you are writing a story or message to the player. EventBody is contextualized within ContextStory. Write ContextStory in the 3rd person, listing a full story outline contextualized in the prior events from ContextEvents. Ensure that ContextStory and EventBody contain only natural language \n{{/block}}[{
        "OldStory": "{{old_story}}",                        
        "LatestEvents": "{{latest_events}}",
        "NewStory": "{{gen 'Update the story outline' temperature=0.6 max_tokens=150 stop_regex='\\x22|\\n|\.'}}",
        "EventBody": "{{gen 'Craft a subsequent story event aligned to the story outline and player actions' temperature=1.3 max_tokens=200 stop_regex='\\x22|\\n|\.'}}",
        "Title": "{{gen 'Convert the EventBody into a unique news title' temperature=0.4 max_tokens=50 stop_regex='\\x22|\\n|\.'}}",
        "Type": "{{select 'Type' options=interaction_types}}",
        "PossibleActions": [{{#geneach 'Suggest player actions' num_iterations=3 join=', '}}"{{gen 'generate a suggested player action' temperature=0.7 max_tokens=100 stop_regex='\\x22|\\n|\.'}}"{{/geneach}}],
        "Entities": [{{#geneach 'List involved characters dynasties and countries' num_iterations=3 join=', '}}"{{gen 'this' temperature=0.2 max_tokens=10 stop_regex='\\x22|\\n|\.'}}"{{/geneach}}],
        "Impact": "{{select 'Type' options=impact_scores}}",
        "ChosenAction": "",
        "_id": "{{event_sequence}}"
        }]""")


        # Ideas: 
        # Include player personality/emotional state and behavior metrics. Log everything!
        # Apply a meta LLM that identifies hooks/arcs/themes. Insert these events for cohesive storytelling
        # Generate an impact score to each event. This can then be used to prioritize certain events over others.
        # Create a graph / social network analysis to define the relationships between entities. This can then be used to generate events that are more likely to occur based on the relationships between entities based on degree centrality (e.g. central entities). 
        # Rather than filtering twice (first score filter then recency filter), we can use a single filter that combines both. This can be done by using a weighted sum of the two scores. The weights can be tuned to achieve the desired effect.
                                 
        print("Guidance template loaded.")


        results = mq.index("events").search(
        q=query, searchable_attributes=['NewStory', 'EventBody'])

        #Implement code so that weight is given to higher impact and more recent events.

        sorted_hits = sorted(results['hits'], key=lambda x: x['_score'], reverse=True)
        context = [{k: hit[k] for k in ('Title', 'EventBody', 'ChosenAction', '_id') if k in hit} for hit in sorted_hits[:3]]

        # Currently just a filter on recency by sorting by id. This can be improved by using a timestamp or by adding weight directly into the initial query (together with impact).

        context = sorted(context, key=lambda x: x['_id'], reverse=True)
        # context = [{k: hit[k] for k in ('Title', 'EventBody', 'ChosenAction', '_id') if k in hit} for hit in context[:3]]

       
        # Initialize an empty list to hold the extracted information
        extracted_info = []
        old_story = ""

        # Loop through each dictionary in the 'context' list
        for idx, event_item in enumerate(context):
            event_body = event_item.get("EventBody", "Unknown Event")
            chosen_action = event_item.get("ChosenAction", "")
            id = event_item.get("_id", "Unknown ID")
            
            # Format the extracted information and add it to the list
            if idx == 0:
                old_story = event_item.get("NewStory", "Unknown Title")
                extracted_info.append(f"Most recent event:\nEvent #{id}: '{event_body}'. \n\nYou responded with: '{chosen_action}'\n")
            elif idx == 1:
                extracted_info.append(f"Related events (for context):\nEvent #{id}: '{event_body}'. You responded with: '{chosen_action}'")
            elif idx > 1:
                extracted_info.append(f"Event #{id}: '{event_body}'. You responded with: '{chosen_action}'")

        # Join the list into a single string with line breaks
        latest_events = "\n".join(extracted_info)

        # Output the formatted string
        print(latest_events)
        
        event_sequence = int(mq.index("events").get_stats().get("numberOfDocuments", "Unknown number"))
        event_sequence += 1
        event_sequence = str(event_sequence)

        output = JSON_builder(
            latest_events=str(latest_events),
            old_story=str(old_story),
            event_sequence=str(event_sequence),
            interaction_types=interaction_types, impact_scores=impact_scores, llm=llm
        )

        # parse the event into a data model
        print(output)
        output

        event = parser.parse(str(output)).dict(by_alias=True)

        # add the event to a list of events
        event_list = []
        event_list.append(event)

        print(event_list)

        mq.index("events").add_documents(event_list, tensor_fields=["ContextStory", "EventBody"])
                
        global_game_state['event'] = event

    return render_template('event.html', event=event)

if __name__ == '__main__':
    app.run()