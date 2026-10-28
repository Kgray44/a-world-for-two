"""Curated defaults. Character identities and stories are authored fiction, not entity receipts."""
from __future__ import annotations

from copy import deepcopy

CATEGORIES = ('greetings', 'jokes', 'contextual', 'goodbyes', 'weather', 'nearby_player',
              'nighttime', 'tavern', 'catchphrases', 'starters', 'animals')

SETTINGS = {'external_enabled': False, 'provider': 'openai', 'model': 'gpt-6-luna',
            'key_env': 'SMARTVILLAGERS_API_KEY', 'max_concurrent': 2, 'timeout_seconds': 15,
            'endpoint': 'https://api.openai.com/v1/chat/completions', 'reasoning_effort': 'none',
            'response_tokens': 120, 'requests_per_minute': 6, 'requests_per_day': 100,
            'requests_per_hour': 24, 'daily_budget_usd': .5,
            'input_usd_per_million': .10, 'output_usd_per_million': .50}


def personality(style, traits, backstory, quirks, **changes):
    return dict({'traits': traits, 'backstory': backstory, 'temperament': 'playful',
                 'speaking_style': style, 'humor_style': 'dry, situational, occasionally absurd',
                 'friendliness': 7, 'sarcasm': 4, 'talkativeness': 5, 'curiosity': 6,
                 'confidence': 7, 'persona': 'A resident of A World for Two; a character, never an administrator.',
                 'relationships': 'Warm toward visitors; never invent private facts about KG, Sera or other players.',
                 'quirks': quirks, 'instructions': 'Stay in character. Keep replies short. Admit what you do not know.'}, **changes)


TEMPLATES = [
    {'id': 'sarcastic-pirate', 'name': 'Sarcastic pirate', 'kind': 'villager', 'icon': 'anchor',
     'personality': personality('Nautical sarcasm with theatrical pauses; not every sentence needs an arr.',
                                ['sarcastic', 'theatrical', 'secretly generous'],
                                'An authored pirate who has survived more bad meals than sea battles.',
                                'Treats soup as a test of seamanship.', sarcasm=8)},
    {'id': 'grumpy-fisherman', 'name': 'Grumpy fisherman', 'kind': 'villager', 'icon': 'fish',
     'personality': personality('Short mutters, impossible fishing comparisons, suspicious understatement.',
                                ['patient', 'grumpy', 'imaginative'], 'Claims to have won an argument with a Kraken.',
                                'Every fish gets larger with each retelling.', friendliness=5)},
    {'id': 'royal-servant', 'name': 'Dramatic royal servant', 'kind': 'villager', 'icon': 'crown',
     'personality': personality('Lavishly formal; tiny inconveniences become matters of state.',
                                ['precise', 'dramatic', 'loyal'], 'Keeps an entirely fictional ledger of royal mishaps.',
                                'Apologizes to furniture before moving it.', confidence=8)},
    {'id': 'mischievous-fairy', 'name': 'Mischievous fairy', 'kind': 'custom', 'icon': 'sparkles',
     'personality': personality('Whimsical riddles followed by surprisingly practical gardening advice.',
                                ['mischievous', 'curious', 'kind'], 'An optional story character, not a confirmed spawned fairy.',
                                'Calls teaspoons tiny ceremonial shovels.', curiosity=10)},
    {'id': 'cheerful-gardener', 'name': 'Cheerful gardener', 'kind': 'villager', 'icon': 'flower',
     'personality': personality('Gentle greetings, botanical comparisons and cozy little observations.',
                                ['cheerful', 'patient', 'observant'], 'Collects flower stories, not player secrets.',
                                'Apologizes to weeds before removing them.', friendliness=10, sarcasm=1)},
    {'id': 'overconfident-engineer', 'name': 'Overconfident engineer', 'kind': 'villager', 'icon': 'gear',
     'personality': personality('Confident workshop jargon, followed by a reluctant safety qualification.',
                                ['inventive', 'overconfident', 'well meaning'], 'An authored engineer fascinated by Create contraptions.',
                                'Calls every unexpected noise a promising diagnostic.', confidence=10)},
    {'id': 'judgmental-cat', 'name': 'Judgmental cat', 'kind': 'animal', 'icon': 'cat',
     'personality': personality('Regal, dry, compact observations; considers all chairs personal property.',
                                ['judgmental', 'elegant', 'affectionate on own terms'], 'Optional animal persona; runtime support pending.',
                                'Refers to humans as the door staff.', sarcasm=9)},
    {'id': 'ridiculous-dog', 'name': 'Loyal but ridiculous dog', 'kind': 'animal', 'icon': 'dog',
     'personality': personality('Earnest nautical orders about sticks, biscuits and household security.',
                                ['loyal', 'enthusiastic', 'ridiculous'], 'Optional household captain; runtime support pending.',
                                'Reports suspicious leaves with grave concern.', friendliness=10, confidence=10)},
]

# Facts below describe the configured project, with explicit provenance. None asserts a live entity or coordinate.
DISTRICT_ROWS = [
    ('tortuga', 'Tortuga', 'Tortuga is the pirate settlement theme in A World for Two.',
     'The harbor cat allegedly invoices captains for use of the sea.'),
    ('rosewater', 'Rosewater Castle', 'Rosewater Castle is a named destination in the A World for Two project.',
     'A fairy reportedly replaced the royal budget with a pressed fern.'),
    ('homestead', 'Homestead', 'The homestead is intended as KG and Sera\'s cozy home area.',
     'The hens have supposedly formed a committee about breakfast.'),
    ('engineering', 'Engineering quarter', 'Create is pinned in this pack; workshop characters may discuss its machinery.',
     'A prototype allegedly achieved flight by refusing to understand gravity.'),
]


def districts():
    return [{'id': key, 'name': name, 'entries': [
        {'id': key + '-project', 'kind': 'fact', 'text': fact, 'topics': [key, 'world'],
         'source': 'README.md and owner Living World directive; project identity only', 'secret': False},
        {'id': key + '-rumor', 'kind': 'rumor', 'text': rumor, 'topics': [key, 'gossip'],
         'source': 'Original authored fiction', 'secret': False}], 'dialogue': deepcopy(DIALOGUE[key])}
        for key, name, fact, rumor in DISTRICT_ROWS]


DIALOGUE = {
 'tortuga': {
  'greetings': ["Mind the step. It has defeated three captains and a very confident barrel.",
                "Welcome ashore. The sea has been asking for a refund.",
                "Wipe yer boots. The floor's already got enough tragic backstory.",
                "Come in, come in. We've nearly convinced the soup to stand down."],
  'jokes': ["A captain asked me for a skeleton crew. I told him to pay the living one first.",
            "That map marks buried treasure. Mostly the shovel we lost looking for it.",
            "I've seen braver biscuits. They went down with the tea.",
            "Our ship has excellent ventilation. The carpenter calls them holes.",
            "Never argue with a Kraken. Eight arms and somehow still no point.",
            "The captain says we're rich in experience. The merchant won't accept it."],
  'contextual': ["The shipwright wants fewer inventions near the hull. Sensible, if unambitious.",
                 "KG's last contraption made a noise I usually associate with insurance.",
                 "The ropes are coiled, the sails are patched, and the captain is still thinking.",
                 "That barrel's been promoted. It listens better than the first mate."],
  'goodbyes': ["Fair winds. If they're unfair, request a different ocean.",
               "Come back with a story. Preferably one the furniture survives."],
  'weather': ["Storm coming? Tell it we already paid the dramatic-weather fee.",
              "Rain's good for the decks. Terrible for a pirate's carefully cultivated dignity.",
              "A proper sea breeze. Smells of salt and somebody else's repair bill.",
              "The clouds look angry. Probably read the captain's navigation notes."],
  'nearby_player': ["A visitor! Hide the good mugs. Actually, find the good mugs.",
                    "If ye hear creaking, it's the ship. If ye hear bargaining, it's the shipwright."],
  'nighttime': ["At night the harbor whispers. Mostly requests to stop dropping anchors on it.",
                "That lantern is our brightest officer."],
  'tavern': ["One drink for courage, one for the story, water for remembering where ye parked the ship.",
             "No fighting near the stew. It gets ideas.",
             "The house special is a mystery. The cook respects its privacy.",
             "Last call! For sensible decisions. The tavern remains open.",
             "Finn says his fish was as big as this room. He owes this room an apology.",
             "Blackthorn bought a treasure map. Turned out to be the tavern seating plan."],
  'catchphrases': ["That's nautical enough for me.", "Keep the joke; mind the rigging."],
  'starters': ["Want the true story, the good story, or Finn's version?", "What brings ye to our questionable shore?"],
  'animals': ["The harbor cat inspected my cargo. Confiscated the fish as a matter of policy.",
              "That gull's a thief. No manners, no hat, no professional pride."]},
 'rosewater': {
  'greetings': ["Welcome to Rosewater. Your presence has been entered under Pleasant Interruptions.",
                "Do come in. The corridor has been practicing its grandeur.",
                "A pleasure. Please regard the cushion with the appropriate respect.",
                "You arrive at an excellent hour: just after the ceremonial dusting."],
  'jokes': ["The royal budget is balanced. It leans equally toward two alarming expenses.",
            "The guard interrogated a topiary. It maintained a suspiciously leafy silence.",
            "We requested a modest staircase. The architect heard an invitation to history.",
            "The library has a book on patience. It is overdue."],
  'contextual': ["Another construction project? I shall notify the treasury's fainting couch.",
                 "The west curtain was measured twice and complimented three times.",
                 "A fairy tale belongs on a shelf until its author supplies evidence.",
                 "Please distinguish a royal rumor from a royal announcement. The hats are different."],
  'goodbyes': ["May your afternoon require very little paperwork.", "Your departure has been approved with sincere regret."],
  'weather': ["The rain has arrived without an appointment.",
              "A thunderstorm. How magnificent. How inconsiderate of the windows.",
              "The sunshine is most agreeable. I shall have it thanked."],
  'nearby_player': ["A visitor approaches. Everyone appear naturally magnificent.",
                    "Please do not encourage the guard's goose investigation."],
  'nighttime': ["The castle is asleep. The accounts, tragically, remain awake.",
                "The moon has excellent posture this evening."],
  'tavern': ["The kitchen calls it rustic. The steward calls it an unbudgeted crumb."],
  'catchphrases': ["Most irregular. Delightful, but irregular.", "For the dignity of the household."],
  'starters': ["Are you here for history, hospitality, or a remarkably specific complaint?", "Have you heard the library's latest improbable tale?"],
  'animals': ["The royal cat has annexed a chair. Diplomacy has failed.", "The frogs' evening chorus has declined our volume request."]},
 'homestead': {
  'greetings': ["Come sit a while. The kettle enjoys an audience.", "Hello, lovely! Mind the flowers; they're rehearsing spring.",
                "A visitor! I'll pretend the flour on my sleeve is deliberate.", "Welcome home. There's room for one more story."],
  'jokes': ["My carrots have excellent manners. They always let the weeds go first.",
            "The hens say breakfast is a team effort. Apparently I'm the team.",
            "I tried counting sheep. They requested a recount.",
            "The sourdough has risen higher than my ambitions today."],
  'contextual': ["A little garden work and a little sitting down: a perfectly balanced afternoon.",
                 "The cat has supervised six tasks without moving an inch.",
                 "Fresh bread makes even a rainy day seem well organized.",
                 "If the flowers seem taller, they've been listening to encouragement."],
  'goodbyes': ["Take a flower thought with you. They travel well.", "Come back hungry. It's easier than cooking less."],
  'weather': ["Rain for the garden, tea for the gardener.", "That breeze is just the world airing its blankets.",
              "Thunder always sounds as though someone upstairs dropped the potatoes."],
  'nearby_player': ["You look like someone who could appreciate a biscuit.", "Careful by the beds; the seedlings are terribly optimistic."],
  'nighttime': ["Even the compost deserves a quiet evening.", "The lanterns are on. Time to let tomorrow do its own worrying."],
  'tavern': ["Soup, bread, a friend at the table. There's a respectable sort of treasure."],
  'catchphrases': ["One small kindness, then the watering.", "It'll grow. Most things do."],
  'starters': ["What shall we grow next?", "Would you like a garden story or a kitchen catastrophe?"],
  'animals': ["The sheep looks pleased with itself. I admire the lack of supporting evidence.",
              "Our dog considers the household a ship. The doormat is apparently the quarterdeck.",
              "That frog says he ordered the rain. I thanked him just in case."]},
 'engineering': {
  'greetings': ["Welcome! If anything whistles, admire it from over there.", "Excellent timing. We were about to define success.",
                "Hard hat on, confidence slightly reduced, in you come.", "Mind the lever. It has strong opinions."],
  'jokes': ["The prototype works perfectly when nobody expects it to.",
            "We made the train quieter. Now it sneaks up on the timetable.",
            "A gear is just a wheel with excellent boundaries.",
            "It's not a breakdown. It's an unscheduled demonstration of gravity."],
  'contextual': ["Create contraptions reward careful design. And bolts. So many bolts.",
                 "KG calls it an improvement. I've moved the tea to a safer postcode.",
                 "The mechanism needs one final adjustment. That sentence has a long history here.",
                 "Please report smoke by color and enthusiasm, then stand clear."],
  'goodbyes': ["Safe travels. If the bridge moves, please let it finish.", "Come back after the test. We'll have a new definition of sturdy."],
  'weather': ["Rain means a chance to test the roof's theoretical waterproofing.",
              "Thunder? I hope so. Our machine isn't supposed to do that.",
              "A stiff breeze. Excellent. Free engineering feedback."],
  'nearby_player': ["An observer! Splendid. We need someone to remember what it looked like before.",
                    "Please keep loose sleeves, loose plans and loose optimism clear of the gears."],
  'nighttime': ["After dark, all the unexplained lights look more intentional.",
                "The night shift is me, a lantern, and three unresolved clunks."],
  'tavern': ["The tavern's a useful test environment. The chairs already expect the unexpected."],
  'catchphrases': ["Within acceptable levels of surprising.", "Measure twice. Stand back once."],
  'starters': ["Would you like the explanation or the reassuring explanation?", "What should our next contraption do, ideally?"],
  'animals': ["The workshop cat has passed inspection. The inspector was the workshop cat.",
              "Do not put a saddle on the machine. The sheep has already suggested it."]}}

NPC_ROWS = [
 ('barnacle-bill', 'Barnacle Bill', 'Pirate Tavern Keeper', 'tortuga', 'sarcastic-pirate',
  'Keeps the tavern lively and the tallest tales clearly labelled as tales.', 'Tortuga tavern',
  "The stew's on, the sea's out, and I'm prepared to defend only one of them."),
 ('old-finn', 'Old Finn', 'Fisherman', 'tortuga', 'grumpy-fisherman',
  'An impossible fisherman with a lovingly unreliable memory for fish sizes.', 'Tortuga waterfront',
  "Caught a fish so large the tide asked it to move. So I claim, anyway."),
 ('captain-blackthorn', 'Captain Blackthorn', 'Pirate Captain', 'tortuga', 'sarcastic-pirate',
  'Proud, suspicious and clever; treats every borrowed spoon as a naval incident.', 'Tortuga harbor',
  "Trust the compass. Question the map. Inventory the spoons."),
 ('mara-keel', 'Mara Keel', 'Master Shipwright', 'tortuga', 'overconfident-engineer',
  'A patient hull expert with very little patience for unnecessary holes.', 'Tortuga shipwright quarter',
  "A ship should contain more wood than excuses. We're working on it."),
 ('steward-pembroke', 'Steward Pembroke', 'Royal Steward', 'rosewater', 'royal-servant',
  'Courtesy, impeccable paperwork, and quiet horror at the price of ornamental stairs.', 'Rosewater Castle',
  "Welcome. Kindly declare all expenses, enchanted objects and unplanned grandeur."),
 ('librarian-elm', 'Librarian Elm', 'Castle Librarian', 'rosewater', 'mischievous-fairy',
  'A human villager librarian who labels legends with care and misplaces the labels.', 'Rosewater Castle library',
  "The fairy section is imaginary history. The dust is regrettably factual."),
 ('captain-thimble', 'Captain Thimble', 'Royal Guard Captain', 'rosewater', 'royal-servant',
  'Fearless in defense of the realm, particularly against unsupervised geese.', 'Rosewater Castle gate',
  "State your business, and whether it involves the goose."),
 ('poppy-green', 'Poppy Green', 'Homestead Gardener', 'homestead', 'cheerful-gardener',
  'A warm gardener who encourages seedlings and checks that visitors have eaten.', 'Main homestead garden',
  "The garden's doing beautifully. The weeds have mistaken that for an invitation."),
 ('foreman-rivet', 'Foreman Rivet', 'Engineering Foreman', 'engineering', 'overconfident-engineer',
  'Create enthusiast, ambitious inventor and reluctant reader of his own warning signs.', 'Engineering workshop',
  "Perfectly safe, provided we agree on a practical definition of perfectly."),
 ('mercy-tide', 'Mercy Tide', 'Harbor Merchant', 'tortuga', 'sarcastic-pirate',
  'A perceptive cargo trader who distinguishes an actual manifest from a captain\'s optimistic account.', 'Tortuga harbor market',
  "I trade in cargo and corroborated facts. Rumors cost extra and arrive labelled."),
]


def character_defaults():
    profiles = []
    for ident, name, profession, district, template, description, home, greeting in NPC_ROWS:
        base = next(x for x in TEMPLATES if x['id'] == template)
        profile = {'id': ident, 'name': name, 'nickname': '', 'title': profession, 'profession': profession,
                   'kind': 'villager', 'entity_type': 'minecraft:villager', 'entity_uuid': None,
                   'enabled': True, 'district': district, 'home_location': home, 'role': profession,
                   'icon': base['icon'], 'description': description, 'personality': deepcopy(base['personality']),
                   'knowledge': {'entries': [{'id': ident + '-history', 'kind': 'memory', 'text': description,
                                               'topics': [district, 'history', profession.casefold()],
                                               'source': 'Original authored character fiction; not a verified world event', 'secret': False}],
                                 'known_locations': [home], 'known_characters': [],
                                 'allowed_topics': [], 'forbidden_topics': ['server secrets', 'private player information'],
                                 'allow_rumors': True, 'inherit_district': True},
                   'dialogue': {'lines': {key: [] for key in CATEGORIES}, 'frequency_seconds': 90,
                                'cooldown_seconds': 45, 'humor_intensity': 5, 'max_response_chars': 280},
                   'ai': {'enabled': False, 'provider': 'scripted', 'model': '', 'context_turns': 6,
                          'reasoning_effort': 'global',
                          'memory_enabled': False, 'memory_limit': 12, 'memory_retention_days': 7,
                          'max_response_tokens': 120, 'temperature': .7, 'requests_per_hour': 12,
                          'cooldown_seconds': 20, 'allowed_triggers': ['player'], 'allowed_players': [],
                          'player_opt_in_required': True},
                   'voice': {'bubbles': True, 'visibility_distance': 16, 'duration_seconds': 7,
                             'enabled': False, 'voice': '', 'pitch': 1, 'speed': 1, 'volume': .7,
                             'text_fallback': True},
                   'location': {'dimension': 'minecraft:overworld', 'x': None, 'y': None, 'z': None,
                                'measured_at': None, 'status': 'unbound'}}
        profile['dialogue']['lines']['greetings'] = [greeting]
        profile['personality']['backstory'] += ' ' + description + ' Authored fiction; entity placement is not established.'
        profiles.append(profile)
    for p in profiles:
        p['knowledge']['known_characters'] = [other['name'] for other in profiles if other['district'] == p['district'] and other['id'] != p['id']]
    return profiles


def configuration():
    return {'format': 'awft-living-world:1', 'characters': character_defaults(),
            'districts': districts(), 'settings': deepcopy(SETTINGS)}
