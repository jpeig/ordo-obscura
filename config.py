class Config:
    REDIS_URL = "redis://redis:6379/0"
    RQ_REDIS_URL = REDIS_URL
    OOB_HOST_WS = 'host.docker.internal:5005'
    OOB_HOST_HTTP = 'host.docker.internal:5000'
    OOB_URI_WS = f'ws://{OOB_HOST_WS}/api/v1/stream'
    OOB_URI_HTTP = f'http://{OOB_HOST_HTTP}/api/v1/generate'
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 8001
    SKIP_GEN_MISSION = False
    SKIP_GEN_NARRATIVE = True
    SKIP_GEN_EVENT = False
    SKIP_GEN_STATE = True
    SKIP_VAL_NARRATIVE = """{
    "player_background": "As an aspiring entrepreneur living during the Dutch Golden Age, you grew up surrounded by the opulent splendor of the Baroque era. Born in a small village near the river Vecht, you were captivated by tales of adventure and wealth brought back by traders returning from faraway lands.",
    "player_lifestyle": "Now settled in Amsterdam, you spend your days navigating the intricate web of politics, commerce, and diplomacy that defined the era. Your home, De Vijverhof, serves as both your refuge and hub of activity, filled with books, maps, and curiosities collected from your travels.",
    "player_standing": "Despite being relatively unknown outside of your inner circle, your reputation precedes you amongst those who appreciate innovation and calculated risk-taking. Some view you with suspicion, while others see potential in your unique perspective and willingness to challenge established norms."
}"""
    SKIP_VAL_MISSION = """{
    "missions": {
        "mission_1": {
            "title": "The Art Collector",
            "narrative": "As an avid collector of rare artifacts and paintings, you receive word of a secret auction taking place at the mansion of a recently deceased nobleman. Rumours suggest that priceless works of art and antiques will be up for grabs. But be warned, there are many other collectors eager to snatch them away from you.",
            "closure_conditions": "Successfully acquire three rare pieces of artwork valued above 50 guilders."
        },
        "mission_2": {
            "title": "A Risky Investment",
            "narrative": "Rumour has it that a new breed of tulips has been discovered in the Far East. These 'rare' bulbs promise to yield flowers unlike anything ever seen before. Many investors are rushing to buy these precious commodities, hoping to strike gold. Should you join them? Or should you play it safe and wait for more reliable investments to emerge?",
            "closure_conditions": "Invest in either the tulip bulb market or another investment option, resulting in either substantial gains or losses."
        },
        "mission_3": {
            "title": "The Secret Society",
            "narrative": "Whispers of a clandestine group operating behind closed doors have reached your ears. Their goals remain obscured, but they seem to possess immense power and influence. Are they friend or foe? And what secrets do they hold that could change the course of history itself?",
            "closure_conditions": "Uncover the true identity and motives of the secret society, potentially aligning yourself with them or becoming their greatest enemy."
        }
    }
}"""
    SKIP_VAL_EVENT = """{}"""
    SKIP_VAL_STATE = {'name': 'My Empire', 'children': [
        {'name': 'De Vijverhof', 'type': 'Location', 'significance': 'This is your modest yet charming residence located near the picturesque lake of De Vijver. It serves as both your sanctuary and base of operations.'
        },
        {'name': 'Het Spiekerhuisje', 'type': 'Location', 'significance': 'A small cottage nestled amidst the rolling hills of your estate. This humble abode provides solace after long days spent trading and exploring new lands.'
        },
        {'name': 'De Gouda Waag', 'type': 'Location', 'significance': 'As a prominent merchant, this iconic building represents the heart of your business dealings. Its towering clock tower stands tall over the bustling marketplace below, reminding you of the ticking clock of opportunity.'
        },
        {'name': 'De Keizersgracht', 'type': 'Location', 'significance': "One of Amsterdam's most famous waterways, it connects you to the city's vibrant center and its many opportunities. As you sail along these historic waters, imagine the countless ships that have traversed here before you."
        },
        {'name': 'Your journal', 'type': 'Object', 'significance': 'As a logician, you meticulously document your thoughts, observations, and plans in this journal. It serves as a repository of your ideas and a tool for organizing your thoughts.'
        },
        {'name': 'Your compass', 'type': 'Object', 'significance': 'A trusted companion on your travels, this compass helps guide you through unfamiliar territories and uncharted waters. Without it, getting lost would be easy.'
        },
        {'name': 'Your map collection', 'type': 'Object', 'significance': 'With your thirst for exploration and discovery, you have amassed a vast collection of maps detailing unexplored regions and hidden treasures. They serve as guides to untold adventures and sources of inspiration.'
        },
        {'name': 'Jacob van der Meer', 'type': 'Entity', 'significance': 'As a fellow entrepreneur like you, Jacob has faced similar challenges and successes in his endeavors. He is known for his innovative ideas and willingness to take risks, making him a valuable ally or potential competitor.'
        },
        {'name': 'Maria de Wijk', 'type': 'Entity', 'significance': 'A wealthy widow who shares your love for art and culture. She frequently hosts lavish parties where you can showcase your latest acquisitions and network with other influential individuals. However, her affinity for extravagance could also lead to dangerous debt traps.'
        },
        {'name': 'Jan van den Boek', 'type': 'Entity', 'significance': 'An ambitious young artist seeking recognition and patronage. His talent and passion inspire you, but he sometimes struggles with self-doubt and financial instability. By supporting him, you might not only contribute to the growth of the arts scene but also establish connections within the elite circles.'
        },
        {'name': 'Willem van Dordrecht', 'type': 'Entity', 'significance': 'A powerful merchant rival who constantly seeks ways to undermine your businesses. He is cunning and ruthless, but also highly respected among the elite circles. Keep a close eye on him, as any misstep could cost you everything.'
        },
        {'name': 'Sophie van Leeuwen', 'type': 'Entity', 'significance': 'A renowned historian and scholar who shares your fascination with the past. Her vast knowledge and insights provide valuable perspectives on the events shaping the world around you. Through her circle of intellectuals, she can open doors to exclusive gatherings and opportunities.'
        },
        {'name': 'Lena van der Zee', 'type': 'Entity', 'significance': 'A skilled spy and agent working undercover for the Dutch East India Company. With her sharp mind and ability to blend seamlessly into society, she gathers crucial information about foreign powers and their intentions. Though she operates in secrecy, her intelligence can prove vital to your strategic decisions.'
        }
    ]
}
    
    SKIP_VAL_PLACES = {'De Vijverhof': {'significance': 'This is your modest yet charming residence located near the picturesque lake of De Vijver. It serves as both your sanctuary and base of operations.', 'owner': 'Jorrit', 'significant': True}, 'Het Spiekerhuisje': {'significance': 'A small cottage nestled amidst the rolling hills of your estate. This humble abode provides solace after long days spent trading and exploring new lands.', 'owner': 'Jorrit', 'significant': True}, 'De Gouda Waag': {'significance': 'As a prominent merchant, this iconic building represents the heart of your business dealings. Its towering clock tower stands tall over the bustling marketplace below, reminding you of the ticking clock of opportunity.', 'owner': 'Guild of Tulip Merchants', 'significant': True}, 'De Keizersgracht': {'significance': "One of Amsterdam's most famous waterways, it connects you to the city's vibrant center and its many opportunities. As you sail along these historic waters, imagine the countless ships that have traversed here before you.", 'owner': 'City of Amsterdam', 'significant': True}}
    SKIP_VAL_PEOPLE = {'Jacob van der Meer': {'significance': 'As a fellow entrepreneur like you, Jacob has faced similar challenges and successes in his endeavors. He is known for his innovative ideas and willingness to take risks, making him a valuable ally or fierce competitor depending on your relationship.', 'location': 'The Spice Market', 'disposition': 'Neutral', 'significant': True}, 'Maria de Wijk': {'significance': 'A wealthy widow who shares your love for art and culture. She frequently hosts lavish parties where you can showcase your latest acquisitions and network with other influential individuals. However, her affinity for extravagance could also lead to dangerous debt traps.', 'location': 'Her mansion in the Jordaan district', 'disposition': 'Friendly', 'significant': True}, 'Jan van den Boek': {'significance': 'An ambitious young artist seeking recognition and patronage. His talent and passion inspire you, but he is also prone to reckless behavior and poor decision-making. Whether you choose to mentor him or exploit his talents remains to be seen.', 'location': 'His studio in the Nieuwstraat', 'disposition': 'Respectful', 'significant': True}, 'Adriaen van der Stok': {'significance': 'A powerful merchant rival who controls much of the trade in spices and exotic goods. He is cunning and ruthless, but also highly respected for his business acumen. Keep a close eye on him, lest he steal away your hard-earned profits.', 'location': 'His warehouse by the harbor', 'disposition': 'Hostile', 'significant': True}, 'Sophie van Delft': {'significance': 'A renowned historian and scholar who studies the rise and fall of empires throughout history. Her insights into politics, economics, and society provide valuable lessons for navigating the ever-changing landscape of power dynamics. She is also rumored to possess knowledge about ancient artifacts hidden across Europe.', 'location': 'The University Library', 'disposition': 'Curious', 'significant': True}, 'Lena van Leeuwen': {'significance': 'A skilled physician and scientist who works tirelessly to advance medical knowledge during a time when superstition still holds sway. Despite being ostracized by some for her unconventional views, she continues to push boundaries and challenge traditional beliefs.', 'location': 'The Botanical Gardens', 'disposition': 'Inquisitive', 'significant': True}}
    SKIP_VAL_OBJECTS = {'Your journal': {'significance': 'As a logician, you meticulously document your thoughts, observations, and plans in this journal. It serves as a repository of your ideas and a tool for organizing your thoughts.', 'location': 'In your pocket or bag.', 'owner': 'You', 'significant': True}, 'Your compass': {'significance': 'A trusted companion on your travels, this compass helps guide you through unfamiliar territories and ensures you never get lost. With it, you can navigate even the most treacherous landscapes.', 'location': 'Attached to your belt or hanging around your neck.', 'owner': 'You', 'significant': True}, 'Your map collection': {'significance': 'Your extensive collection of maps serves as a visual representation of the vast world beyond your immediate surroundings. They offer insight into unexplored regions and potential routes for future adventures.', 'location': 'Stowed safely in your home or traveling pack.', 'owner': 'You', 'significant': True}}
