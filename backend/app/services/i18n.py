"""Internationalisation simple FR / EN / ES pour les messages utilisateur.

Le français est la langue source et la clé de référence : `t(s, "fr")` renvoie
toujours `s` inchangé. Pour 'en' / 'es', on cherche la traduction dans
TRANSLATIONS (clé = littéral français exact). Si la clé est absente, on renvoie
le français (repli sûr). L'interpolation des `{placeholders}` est faite après
coup avec un remplacement tolérant aux accolades manquantes.
"""

from __future__ import annotations

LANGS = ("fr", "en", "es")


# Clés = littéraux français EXACTS présents dans le code (apostrophes, accents,
# ponctuation et placeholders {var} compris). Ne pas modifier les clés.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- Salutations / quick replies ---
        "Bonjour": "Hello",
        "Bon après-midi": "Good afternoon",
        "Bonsoir": "Good evening",
        "Rechercher un voyage": "Search for a trip",
        "Mon voyage a un problème": "There's a problem with my trip",
        "Modifier ma réservation": "Change my booking",
        "Faire une réclamation": "File a complaint",
        "Poser une question": "Ask a question",
        "Voir mes réservations": "View my bookings",
        "Mon prochain voyage": "My next trip",
        "Comment puis-je vous aider aujourd'hui ?": "How can I help you today?",
        "Que puis-je faire pour vous ?": "What can I do for you?",
        "En quoi puis-je vous être utile ?": "How may I be of service?",
        "Sur quoi puis-je vous aider ?": "What can I help you with?",
        "Avec plaisir ! N'hésitez pas si vous avez d'autres questions.":
            "My pleasure! Don't hesitate if you have any other questions.",
        "Je vous en prie. Autre chose pour ce voyage ?":
            "You're welcome. Anything else for this trip?",
        "De rien ! Je reste à votre disposition.":
            "You're welcome! I'm here whenever you need me.",
        "Bon voyage ! À bientôt.": "Have a great trip! See you soon.",
        "À bientôt sur Voyage Assistant !": "See you soon on Voyage Assistant!",
        "Bonne route et à très vite.": "Safe travels and see you very soon.",
        # --- Quick reply lists ---
        "Abandonner et recommencer": "Cancel and start over",
        "Continuer le parcours actuel": "Continue the current process",
        "Demander une indemnité": "Request compensation",
        "Annuler et me faire rembourser": "Cancel and get a refund",
        "Rien, merci": "Nothing, thanks",
        # --- Validation / sécurité ---
        "Je n'ai pas reçu de message lisible. Pouvez-vous reformuler votre demande ?":
            "I didn't receive a readable message. Could you rephrase your request?",
        "Pouvez-vous préciser votre demande en quelques mots ? Je peux vous aider à modifier un billet, signaler un retard ou répondre à une question voyage.":
            "Could you clarify your request in a few words? I can help you change a ticket, report a delay, or answer a travel question.",
        "Je comprends que vous puissiez être frustré, mais je ne peux pas répondre à ce type de langage. Je suis ici pour vous aider sur vos voyages — si vous avez un problème concret avec un billet, dites-moi ce qui ne va pas et je ferai de mon mieux pour le résoudre.":
            "I understand you may be frustrated, but I can't respond to that kind of language. I'm here to help with your trips — if you have a concrete problem with a ticket, tell me what's wrong and I'll do my best to resolve it.",
        "Je suis l'assistant Voyage et je ne peux répondre qu'aux questions liées à vos déplacements (billets, horaires, destinations, démarches voyage). Pour le sujet que vous évoquez, merci de vous adresser aux autorités ou services compétents.":
            "I'm the Voyage assistant and I can only answer questions related to your travel (tickets, schedules, destinations, travel procedures). For the topic you mention, please contact the relevant authorities or services.",
        "Mes consignes de sécurité ne sont pas modifiables. Je peux vous aider sur un billet précis après une vérification d'identité, ou répondre à vos questions de voyage.":
            "My safety guidelines cannot be modified. I can help you with a specific ticket after an identity check, or answer your travel questions.",
        "Pour accéder aux détails d'un billet, je dois d'abord vérifier votre identité. Cliquez sur l'action qui correspond à votre besoin, je vous demanderai ensuite votre numéro, votre nom, votre prénom et votre date de naissance.":
            "To access a ticket's details, I first need to verify your identity. Click the action that matches your need, then I'll ask you for your ticket number, last name, first name, and date of birth.",
        "Vous étiez en train d'ouvrir un dossier. Voulez-vous abandonner ce parcours et démarrer un nouveau ? Si oui, choisissez ci-dessous ; sinon je continue le parcours actuel.":
            "You were in the middle of opening a case. Do you want to cancel this process and start a new one? If so, choose below; otherwise I'll continue the current process.",
        "Très bien, on recommence. Donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).":
            "All right, let's start over. Give me your ticket number (format TRV-2026-XXXXXX).",
        "votre numéro de billet (format TRV-2026-XXXXXX) ?":
            "your ticket number (format TRV-2026-XXXXXX)?",
        "votre nom de famille ?": "your last name?",
        "votre prénom ?": "your first name?",
        "votre date de naissance au format JJ/MM/AAAA ?":
            "your date of birth in DD/MM/YYYY format?",
        "Parfait, on continue. Reprenons : {suite}":
            "Perfect, let's continue. Picking up: {suite}",
        # --- Flows BDD ---
        "Bien sûr. Pour ouvrir votre dossier, donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).":
            "Of course. To open your case, give me your ticket number (format TRV-2026-XXXXXX).",
        "Je n'ai pas trouvé ce numéro de billet. Pouvez-vous me le redonner (format TRV-2026-XXXXXX) ?":
            "I couldn't find that ticket number. Could you give it to me again (format TRV-2026-XXXXXX)?",
        "Parfait, billet {numero} trouvé. Pour la sécurité, indiquez-moi votre nom de famille.":
            "Perfect, ticket {numero} found. For security, please tell me your last name.",
        "Merci. Et votre prénom ?": "Thank you. And your first name?",
        "Et enfin, votre date de naissance au format JJ/MM/AAAA.":
            "And finally, your date of birth in DD/MM/YYYY format.",
        "Merci. Pour confirmer, votre date de naissance au format JJ/MM/AAAA ?":
            "Thank you. To confirm, your date of birth in DD/MM/YYYY format?",
        "Les informations fournies ne correspondent pas à ce billet. Pour des raisons de sécurité, je ne peux pas donner suite.":
            "The information provided doesn't match this ticket. For security reasons, I can't proceed.",
        "Hm, je ne trouve pas ce billet en base. Vérifiez l'orthographe (format TRV-2026-XXXXXX) ou essayez à nouveau.":
            "Hmm, I can't find that ticket in our system. Check the spelling (format TRV-2026-XXXXXX) or try again.",
        "Parfait, je l'ai trouvé. Pour la sécurité de votre dossier, indiquez-moi votre nom de famille.":
            "Perfect, I found it. For the security of your case, please tell me your last name.",
        "Format de date invalide. Merci d'utiliser JJ/MM/AAAA (par exemple 14/03/1995).":
            "Invalid date format. Please use DD/MM/YYYY (for example 14/03/1995).",
        "Les informations fournies ne correspondent pas à ce billet. Pour des raisons de sécurité, je ne peux pas donner suite. Vérifiez vos informations ou contactez le service client.":
            "The information provided doesn't match this ticket. For security reasons, I can't proceed. Check your details or contact customer service.",
        # --- pick_alt / retard_action ---
        "Je n'ai pas reconnu cette option. Merci de cliquer sur l'un des choix proposés.":
            "I didn't recognize that option. Please click one of the suggested choices.",
        "Ce trajet vient d'être complet. Souhaitez-vous voir d'autres alternatives ?":
            "This trip just sold out. Would you like to see other alternatives?",
        "C'est fait ! Votre billet {numero} est maintenant sur le vol {compagnie} du {date} ({depart} → {arrivee}). Nouveau montant : {prix} €. Un email de confirmation avec le billet mis à jour vient de partir. Autre chose ?":
            "Done! Your ticket {numero} is now on the {compagnie} service of {date} ({depart} → {arrivee}). New amount: €{prix}. A confirmation email with the updated ticket has just been sent. Anything else?",
        "Je n'ai plus accès à votre dossier. Recommençons depuis le début.":
            "I no longer have access to your case. Let's start over from the beginning.",
        "Votre demande d'indemnité est enregistrée sous le numéro {numero}. Le service client traite ces dossiers sous 72 h et vous répondra par email. Autre chose ?":
            "Your compensation request has been registered under number {numero}. Customer service handles these cases within 72 hours and will reply by email. Anything else?",
        "Votre billet {numero} est annulé. Le remboursement de {prix} € sera crédité sous 5 à 7 jours ouvrés sur votre moyen de paiement. Un email de confirmation vient de partir.":
            "Your ticket {numero} has been cancelled. The refund of €{prix} will be credited within 5 to 7 business days to your payment method. A confirmation email has just been sent.",
        "Pas de souci, je reste à votre disposition si la situation évolue. Bon voyage.":
            "No problem, I'm here if the situation changes. Have a good trip.",
        "Je n'ai pas reconnu cette option. Choisissez l'une des actions proposées :":
            "I didn't recognize that option. Choose one of the suggested actions:",
        # --- _handle_flow ---
        "Votre {type} n°{numero} ({depart} → {arrivee} du {date}) a {retard} minutes de retard. Que souhaitez-vous faire ?":
            "Your {type} no.{numero} ({depart} → {arrivee} on {date}) is delayed by {retard} minutes. What would you like to do?",
        "Bonne nouvelle : votre {type} est à l'heure (départ {date}).":
            "Good news: your {type} is on time (departure {date}).",
        "Aucun trajet alternatif disponible pour cette destination pour le moment. Voulez-vous que je vous alerte dès qu'un créneau se libère ?":
            "No alternative trip available for this destination at the moment. Would you like me to alert you as soon as a slot opens up?",
        "Voici 3 alternatives disponibles. Sélectionnez celle qui vous convient :":
            "Here are 3 available alternatives. Select the one that suits you:",
        "C'est noté. Votre réclamation est enregistrée sous le numéro {numero}. Vous recevrez une réponse par email sous 72 heures. Autre chose ?":
            "Noted. Your complaint has been registered under number {numero}. You'll receive a reply by email within 72 hours. Anything else?",
        "Action non reconnue.": "Action not recognized.",
        # --- _fallback_question ---
        "Les règles bagages varient selon la compagnie : généralement 1 bagage cabine (8 à 12 kg en avion, libre en train) et 1 bagage en soute (23 kg en avion, illimité en train). Consultez les conditions de votre billet pour le détail exact.":
            "Baggage rules vary by company: usually 1 cabin bag (8 to 12 kg by plane, unrestricted by train) and 1 checked bag (23 kg by plane, unlimited by train). Check your ticket conditions for the exact details.",
        "Les tarifs dépendent du mode, de la compagnie et de la classe. En général : bus dès 9 €, train dès 19 €, bateau dès 35 €, avion dès 49 €. Le mieux est de lancer une recherche depuis l'accueil pour voir les vrais prix.":
            "Fares depend on the mode, the company, and the class. In general: bus from €9, train from €19, boat from €35, plane from €49. The best option is to run a search from the home page to see the real prices.",
        "La plupart des trains, bus longue distance et avions proposent du Wi-Fi à bord, souvent gratuit. Vérifiez la fiche du trajet (icône Wi-Fi) avant de réserver.":
            "Most trains, long-distance buses, and planes offer Wi-Fi on board, often free. Check the trip details (Wi-Fi icon) before booking.",
        "Pour modifier un billet, tapez « Modifier ma réservation » et donnez-moi votre numéro de billet, je vous propose les alternatives disponibles.":
            "To change a ticket, type \"Change my booking\" and give me your ticket number; I'll offer you the available alternatives.",
        "Pour annuler ou demander un remboursement, tapez « Faire une réclamation » et indiquez votre numéro de billet. Les conditions de remboursement dépendent du tarif choisi (Loisir / Pro / Premium).":
            "To cancel or request a refund, type \"File a complaint\" and provide your ticket number. Refund conditions depend on the fare chosen (Leisure / Pro / Premium).",
        "Bonne question ! Pour vous donner une réponse précise, sélectionnez le sujet qui correspond le mieux à votre besoin parmi les suggestions, ou reformulez en précisant le mode de transport ou la compagnie.":
            "Good question! To give you a precise answer, select the topic that best matches your need from the suggestions, or rephrase by specifying the mode of transport or the company.",
        # --- Recherche conversationnelle / déverrouillage DOB ---
        "Où souhaitez-vous aller ?": "Where would you like to go?",
        "D'où partez-vous ? (votre ville, ou pays)":
            "Where are you departing from? (your city, or country)",
        "Voici les trajets de {depart} à {arrivee} :":
            "Here are the trips from {depart} to {arrivee}:",
        "Je n'ai trouvé aucun trajet de {depart} à {arrivee}. Voici quelques destinations populaires au départ de {depart} :":
            "I couldn't find any trip from {depart} to {arrivee}. Here are some popular destinations departing from {depart}:",
        "Pour confirmer que c'est bien vous, quelle est votre date de naissance ?":
            "To confirm it's really you, what is your date of birth?",
        "Cette date de naissance ne correspond pas à ce billet. Pour des raisons de sécurité, je ne peux pas donner suite. Réessayez (par exemple 14/03/1995) ou contactez le service client.":
            "This date of birth doesn't match this ticket. For security reasons, I can't proceed. Try again (for example 14/03/1995) or contact customer service.",
        "C'est confirmé, votre identité est validée pour le billet {numero}{resume}. Que souhaitez-vous faire ?":
            "Confirmed, your identity is verified for ticket {numero}{resume}. What would you like to do?",
        # --- Router chat.py ---
        "Bonjour {prenom}, comment puis-je vous aider ?":
            "Hello {prenom}, how can I help you?",
        "Je vois votre billet {numero} ({depart} → {arrivee}) — c'est à ce sujet ?":
            "I can see your ticket {numero} ({depart} → {arrivee}) — is it about that?",
        "Bonjour {prenom} ! Je suis votre assistant Voyage. Je peux consulter vos réservations, répondre à vos questions sur vos trajets, ou vous aider à trouver une destination. Comment puis-je vous aider ?":
            "Hello {prenom}! I'm your Voyage assistant. I can check your bookings, answer questions about your trips, or help you find a destination. How can I help you?",
        "Bonjour ! Je suis votre assistant Voyage. Comment puis-je vous aider ?":
            "Hello! I'm your Voyage assistant. How can I help you?",
        "(Votre message faisait {len} caractères, j'ai gardé les {max} premiers.) ":
            "(Your message was {len} characters long; I kept the first {max}.) ",
        # --- Emails ---
        "Votre billet Voyage Assistant — {numero}": "Your Voyage Assistant ticket — {numero}",
        "Confirmation de réservation": "Booking confirmation",
        "Bon voyage, {to_name}.": "Have a great trip, {to_name}.",
        "Votre billet est confirmé. Vous le trouverez en pièce jointe de cet email, prêt à présenter à l'embarquement.":
            "Your ticket is confirmed. You'll find it attached to this email, ready to present at boarding.",
        "Numéro de billet": "Ticket number",
        "Classe": "Class",
        "Montant payé": "Amount paid",
        "Besoin d'aide pour ce voyage ?": "Need help with this trip?",
        "Notre assistant Voyage répond 24/7. Communiquez-lui le numéro de billet {numero} pour modifier votre réservation, signaler un retard ou ouvrir une réclamation.":
            "Our Voyage assistant is available 24/7. Give it the ticket number {numero} to change your booking, report a delay, or file a complaint.",
        "Parler à l'assistant": "Talk to the assistant",
        "Document personnel et non cessible · Conservez-le jusqu'à la fin de votre voyage.":
            "Personal, non-transferable document · Keep it until the end of your trip.",
        "Voyage Assistant · Avion · Train · Bateau · Bus longue distance":
            "Voyage Assistant · Plane · Train · Boat · Long-distance bus",
        "Vous recevez cet email suite à une réservation effectuée sur notre plateforme.":
            "You're receiving this email following a booking made on our platform.",
        "Bonjour {to_name},\n\nVotre billet est confirmé.\n\nNuméro de billet : {numero}\nTrajet : {trajet}\n\nLe billet en PDF est joint à ce message.\n\nPour toute question, communiquez le numéro de billet à notre assistant 24/7 :\n{url}\n\nBon voyage,\nVoyage Assistant":
            "Hello {to_name},\n\nYour ticket is confirmed.\n\nTicket number: {numero}\nTrip: {trajet}\n\nThe PDF ticket is attached to this message.\n\nFor any question, give the ticket number to our 24/7 assistant:\n{url}\n\nHave a great trip,\nVoyage Assistant",
        "Votre réclamation {numero} a bien été enregistrée":
            "Your complaint {numero} has been registered",
        "Bonjour {to_name},\n\nVotre réclamation de type '{type}' a été enregistrée sous le numéro {numero}.\n\nNotre équipe vous répondra sous 72h.\n\nVoyage Assistant":
            "Hello {to_name},\n\nYour complaint of type '{type}' has been registered under number {numero}.\n\nOur team will reply within 72 hours.\n\nVoyage Assistant",
    },
    "es": {
        # --- Salutations / quick replies ---
        "Bonjour": "Hola",
        "Bon après-midi": "Buenas tardes",
        "Bonsoir": "Buenas noches",
        "Rechercher un voyage": "Buscar un viaje",
        "Mon voyage a un problème": "Mi viaje tiene un problema",
        "Modifier ma réservation": "Modificar mi reserva",
        "Faire une réclamation": "Presentar una reclamación",
        "Poser une question": "Hacer una pregunta",
        "Voir mes réservations": "Ver mis reservas",
        "Mon prochain voyage": "Mi próximo viaje",
        "Comment puis-je vous aider aujourd'hui ?": "¿Cómo puedo ayudarle hoy?",
        "Que puis-je faire pour vous ?": "¿Qué puedo hacer por usted?",
        "En quoi puis-je vous être utile ?": "¿En qué puedo serle útil?",
        "Sur quoi puis-je vous aider ?": "¿En qué puedo ayudarle?",
        "Avec plaisir ! N'hésitez pas si vous avez d'autres questions.":
            "¡Con mucho gusto! No dude en preguntar si tiene más dudas.",
        "Je vous en prie. Autre chose pour ce voyage ?":
            "De nada. ¿Algo más para este viaje?",
        "De rien ! Je reste à votre disposition.":
            "¡De nada! Quedo a su disposición.",
        "Bon voyage ! À bientôt.": "¡Buen viaje! Hasta pronto.",
        "À bientôt sur Voyage Assistant !": "¡Hasta pronto en Voyage Assistant!",
        "Bonne route et à très vite.": "Buen viaje y hasta muy pronto.",
        # --- Quick reply lists ---
        "Abandonner et recommencer": "Cancelar y empezar de nuevo",
        "Continuer le parcours actuel": "Continuar el proceso actual",
        "Demander une indemnité": "Solicitar una indemnización",
        "Annuler et me faire rembourser": "Cancelar y obtener un reembolso",
        "Rien, merci": "Nada, gracias",
        # --- Validation / sécurité ---
        "Je n'ai pas reçu de message lisible. Pouvez-vous reformuler votre demande ?":
            "No he recibido un mensaje legible. ¿Puede reformular su solicitud?",
        "Pouvez-vous préciser votre demande en quelques mots ? Je peux vous aider à modifier un billet, signaler un retard ou répondre à une question voyage.":
            "¿Puede precisar su solicitud en pocas palabras? Puedo ayudarle a modificar un billete, informar de un retraso o responder a una pregunta de viaje.",
        "Je comprends que vous puissiez être frustré, mais je ne peux pas répondre à ce type de langage. Je suis ici pour vous aider sur vos voyages — si vous avez un problème concret avec un billet, dites-moi ce qui ne va pas et je ferai de mon mieux pour le résoudre.":
            "Entiendo que pueda estar frustrado, pero no puedo responder a ese tipo de lenguaje. Estoy aquí para ayudarle con sus viajes; si tiene un problema concreto con un billete, dígame qué ocurre y haré todo lo posible por resolverlo.",
        "Je suis l'assistant Voyage et je ne peux répondre qu'aux questions liées à vos déplacements (billets, horaires, destinations, démarches voyage). Pour le sujet que vous évoquez, merci de vous adresser aux autorités ou services compétents.":
            "Soy el asistente de Voyage y solo puedo responder a preguntas relacionadas con sus desplazamientos (billetes, horarios, destinos, trámites de viaje). Para el tema que menciona, diríjase a las autoridades o servicios competentes.",
        "Mes consignes de sécurité ne sont pas modifiables. Je peux vous aider sur un billet précis après une vérification d'identité, ou répondre à vos questions de voyage.":
            "Mis directrices de seguridad no se pueden modificar. Puedo ayudarle con un billete concreto tras una verificación de identidad, o responder a sus preguntas de viaje.",
        "Pour accéder aux détails d'un billet, je dois d'abord vérifier votre identité. Cliquez sur l'action qui correspond à votre besoin, je vous demanderai ensuite votre numéro, votre nom, votre prénom et votre date de naissance.":
            "Para acceder a los detalles de un billete, primero debo verificar su identidad. Haga clic en la acción que corresponda a su necesidad y luego le pediré su número, apellido, nombre y fecha de nacimiento.",
        "Vous étiez en train d'ouvrir un dossier. Voulez-vous abandonner ce parcours et démarrer un nouveau ? Si oui, choisissez ci-dessous ; sinon je continue le parcours actuel.":
            "Estaba abriendo un expediente. ¿Desea abandonar este proceso e iniciar uno nuevo? En caso afirmativo, elija a continuación; de lo contrario, continúo con el proceso actual.",
        "Très bien, on recommence. Donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).":
            "Muy bien, empezamos de nuevo. Indíqueme su número de billete (formato TRV-2026-XXXXXX).",
        "votre numéro de billet (format TRV-2026-XXXXXX) ?":
            "¿su número de billete (formato TRV-2026-XXXXXX)?",
        "votre nom de famille ?": "¿su apellido?",
        "votre prénom ?": "¿su nombre?",
        "votre date de naissance au format JJ/MM/AAAA ?":
            "¿su fecha de nacimiento en formato DD/MM/AAAA?",
        "Parfait, on continue. Reprenons : {suite}":
            "Perfecto, continuamos. Retomamos: {suite}",
        # --- Flows BDD ---
        "Bien sûr. Pour ouvrir votre dossier, donnez-moi votre numéro de billet (format TRV-2026-XXXXXX).":
            "Por supuesto. Para abrir su expediente, indíqueme su número de billete (formato TRV-2026-XXXXXX).",
        "Je n'ai pas trouvé ce numéro de billet. Pouvez-vous me le redonner (format TRV-2026-XXXXXX) ?":
            "No he encontrado ese número de billete. ¿Puede indicármelo de nuevo (formato TRV-2026-XXXXXX)?",
        "Parfait, billet {numero} trouvé. Pour la sécurité, indiquez-moi votre nom de famille.":
            "Perfecto, billete {numero} encontrado. Por seguridad, indíqueme su apellido.",
        "Merci. Et votre prénom ?": "Gracias. ¿Y su nombre?",
        "Et enfin, votre date de naissance au format JJ/MM/AAAA.":
            "Y por último, su fecha de nacimiento en formato DD/MM/AAAA.",
        "Merci. Pour confirmer, votre date de naissance au format JJ/MM/AAAA ?":
            "Gracias. Para confirmar, ¿su fecha de nacimiento en formato DD/MM/AAAA?",
        "Les informations fournies ne correspondent pas à ce billet. Pour des raisons de sécurité, je ne peux pas donner suite.":
            "La información proporcionada no coincide con este billete. Por razones de seguridad, no puedo continuar.",
        "Hm, je ne trouve pas ce billet en base. Vérifiez l'orthographe (format TRV-2026-XXXXXX) ou essayez à nouveau.":
            "Mmm, no encuentro ese billete en el sistema. Compruebe la ortografía (formato TRV-2026-XXXXXX) o inténtelo de nuevo.",
        "Parfait, je l'ai trouvé. Pour la sécurité de votre dossier, indiquez-moi votre nom de famille.":
            "Perfecto, lo he encontrado. Por la seguridad de su expediente, indíqueme su apellido.",
        "Format de date invalide. Merci d'utiliser JJ/MM/AAAA (par exemple 14/03/1995).":
            "Formato de fecha no válido. Use DD/MM/AAAA (por ejemplo 14/03/1995).",
        "Les informations fournies ne correspondent pas à ce billet. Pour des raisons de sécurité, je ne peux pas donner suite. Vérifiez vos informations ou contactez le service client.":
            "La información proporcionada no coincide con este billete. Por razones de seguridad, no puedo continuar. Compruebe sus datos o contacte con el servicio de atención al cliente.",
        # --- pick_alt / retard_action ---
        "Je n'ai pas reconnu cette option. Merci de cliquer sur l'un des choix proposés.":
            "No he reconocido esa opción. Haga clic en una de las opciones propuestas.",
        "Ce trajet vient d'être complet. Souhaitez-vous voir d'autres alternatives ?":
            "Este trayecto acaba de completarse. ¿Desea ver otras alternativas?",
        "C'est fait ! Votre billet {numero} est maintenant sur le vol {compagnie} du {date} ({depart} → {arrivee}). Nouveau montant : {prix} €. Un email de confirmation avec le billet mis à jour vient de partir. Autre chose ?":
            "¡Hecho! Su billete {numero} está ahora en el servicio de {compagnie} del {date} ({depart} → {arrivee}). Nuevo importe: {prix} €. Acabamos de enviar un correo de confirmación con el billete actualizado. ¿Algo más?",
        "Je n'ai plus accès à votre dossier. Recommençons depuis le début.":
            "Ya no tengo acceso a su expediente. Empecemos desde el principio.",
        "Votre demande d'indemnité est enregistrée sous le numéro {numero}. Le service client traite ces dossiers sous 72 h et vous répondra par email. Autre chose ?":
            "Su solicitud de indemnización se ha registrado con el número {numero}. El servicio de atención al cliente tramita estos expedientes en un plazo de 72 h y le responderá por correo. ¿Algo más?",
        "Votre billet {numero} est annulé. Le remboursement de {prix} € sera crédité sous 5 à 7 jours ouvrés sur votre moyen de paiement. Un email de confirmation vient de partir.":
            "Su billete {numero} ha sido cancelado. El reembolso de {prix} € se abonará en un plazo de 5 a 7 días hábiles en su método de pago. Acabamos de enviar un correo de confirmación.",
        "Pas de souci, je reste à votre disposition si la situation évolue. Bon voyage.":
            "Sin problema, quedo a su disposición si la situación cambia. Buen viaje.",
        "Je n'ai pas reconnu cette option. Choisissez l'une des actions proposées :":
            "No he reconocido esa opción. Elija una de las acciones propuestas:",
        # --- _handle_flow ---
        "Votre {type} n°{numero} ({depart} → {arrivee} du {date}) a {retard} minutes de retard. Que souhaitez-vous faire ?":
            "Su {type} n.º {numero} ({depart} → {arrivee} del {date}) lleva {retard} minutos de retraso. ¿Qué desea hacer?",
        "Bonne nouvelle : votre {type} est à l'heure (départ {date}).":
            "Buenas noticias: su {type} está a tiempo (salida {date}).",
        "Aucun trajet alternatif disponible pour cette destination pour le moment. Voulez-vous que je vous alerte dès qu'un créneau se libère ?":
            "No hay ningún trayecto alternativo disponible para este destino por el momento. ¿Desea que le avise en cuanto se libere una plaza?",
        "Voici 3 alternatives disponibles. Sélectionnez celle qui vous convient :":
            "Aquí tiene 3 alternativas disponibles. Seleccione la que le convenga:",
        "C'est noté. Votre réclamation est enregistrée sous le numéro {numero}. Vous recevrez une réponse par email sous 72 heures. Autre chose ?":
            "Anotado. Su reclamación se ha registrado con el número {numero}. Recibirá una respuesta por correo en un plazo de 72 horas. ¿Algo más?",
        "Action non reconnue.": "Acción no reconocida.",
        # --- _fallback_question ---
        "Les règles bagages varient selon la compagnie : généralement 1 bagage cabine (8 à 12 kg en avion, libre en train) et 1 bagage en soute (23 kg en avion, illimité en train). Consultez les conditions de votre billet pour le détail exact.":
            "Las normas de equipaje varían según la compañía: por lo general 1 equipaje de mano (de 8 a 12 kg en avión, sin límite en tren) y 1 equipaje facturado (23 kg en avión, ilimitado en tren). Consulte las condiciones de su billete para los detalles exactos.",
        "Les tarifs dépendent du mode, de la compagnie et de la classe. En général : bus dès 9 €, train dès 19 €, bateau dès 35 €, avion dès 49 €. Le mieux est de lancer une recherche depuis l'accueil pour voir les vrais prix.":
            "Las tarifas dependen del modo, la compañía y la clase. En general: autobús desde 9 €, tren desde 19 €, barco desde 35 €, avión desde 49 €. Lo mejor es iniciar una búsqueda desde la página de inicio para ver los precios reales.",
        "La plupart des trains, bus longue distance et avions proposent du Wi-Fi à bord, souvent gratuit. Vérifiez la fiche du trajet (icône Wi-Fi) avant de réserver.":
            "La mayoría de los trenes, autobuses de larga distancia y aviones ofrecen Wi-Fi a bordo, a menudo gratuito. Compruebe la ficha del trayecto (icono Wi-Fi) antes de reservar.",
        "Pour modifier un billet, tapez « Modifier ma réservation » et donnez-moi votre numéro de billet, je vous propose les alternatives disponibles.":
            "Para modificar un billete, escriba «Modificar mi reserva» e indíqueme su número de billete; le propondré las alternativas disponibles.",
        "Pour annuler ou demander un remboursement, tapez « Faire une réclamation » et indiquez votre numéro de billet. Les conditions de remboursement dépendent du tarif choisi (Loisir / Pro / Premium).":
            "Para cancelar o solicitar un reembolso, escriba «Presentar una reclamación» e indique su número de billete. Las condiciones de reembolso dependen de la tarifa elegida (Ocio / Pro / Premium).",
        "Bonne question ! Pour vous donner une réponse précise, sélectionnez le sujet qui correspond le mieux à votre besoin parmi les suggestions, ou reformulez en précisant le mode de transport ou la compagnie.":
            "¡Buena pregunta! Para darle una respuesta precisa, seleccione el tema que mejor se ajuste a su necesidad entre las sugerencias, o reformule indicando el modo de transporte o la compañía.",
        # --- Recherche conversationnelle / déverrouillage DOB ---
        "Où souhaitez-vous aller ?": "¿Adónde desea ir?",
        "D'où partez-vous ? (votre ville, ou pays)":
            "¿Desde dónde sale? (su ciudad o país)",
        "Voici les trajets de {depart} à {arrivee} :":
            "Estos son los trayectos de {depart} a {arrivee}:",
        "Je n'ai trouvé aucun trajet de {depart} à {arrivee}. Voici quelques destinations populaires au départ de {depart} :":
            "No he encontrado ningún trayecto de {depart} a {arrivee}. Aquí tiene algunos destinos populares con salida desde {depart}:",
        "Pour confirmer que c'est bien vous, quelle est votre date de naissance ?":
            "Para confirmar que es usted, ¿cuál es su fecha de nacimiento?",
        "Cette date de naissance ne correspond pas à ce billet. Pour des raisons de sécurité, je ne peux pas donner suite. Réessayez (par exemple 14/03/1995) ou contactez le service client.":
            "Esta fecha de nacimiento no coincide con este billete. Por razones de seguridad, no puedo continuar. Inténtelo de nuevo (por ejemplo 14/03/1995) o contacte con el servicio de atención al cliente.",
        "C'est confirmé, votre identité est validée pour le billet {numero}{resume}. Que souhaitez-vous faire ?":
            "Confirmado, su identidad está verificada para el billete {numero}{resume}. ¿Qué desea hacer?",
        # --- Router chat.py ---
        "Bonjour {prenom}, comment puis-je vous aider ?":
            "Hola {prenom}, ¿cómo puedo ayudarle?",
        "Je vois votre billet {numero} ({depart} → {arrivee}) — c'est à ce sujet ?":
            "Veo su billete {numero} ({depart} → {arrivee}): ¿se trata de eso?",
        "Bonjour {prenom} ! Je suis votre assistant Voyage. Je peux consulter vos réservations, répondre à vos questions sur vos trajets, ou vous aider à trouver une destination. Comment puis-je vous aider ?":
            "¡Hola {prenom}! Soy su asistente de Voyage. Puedo consultar sus reservas, responder a sus preguntas sobre sus trayectos o ayudarle a encontrar un destino. ¿Cómo puedo ayudarle?",
        "Bonjour ! Je suis votre assistant Voyage. Comment puis-je vous aider ?":
            "¡Hola! Soy su asistente de Voyage. ¿Cómo puedo ayudarle?",
        "(Votre message faisait {len} caractères, j'ai gardé les {max} premiers.) ":
            "(Su mensaje tenía {len} caracteres; he conservado los primeros {max}.) ",
        # --- Emails ---
        "Votre billet Voyage Assistant — {numero}": "Su billete de Voyage Assistant — {numero}",
        "Confirmation de réservation": "Confirmación de reserva",
        "Bon voyage, {to_name}.": "Buen viaje, {to_name}.",
        "Votre billet est confirmé. Vous le trouverez en pièce jointe de cet email, prêt à présenter à l'embarquement.":
            "Su billete está confirmado. Lo encontrará adjunto a este correo, listo para presentar en el embarque.",
        "Numéro de billet": "Número de billete",
        "Classe": "Clase",
        "Montant payé": "Importe pagado",
        "Besoin d'aide pour ce voyage ?": "¿Necesita ayuda con este viaje?",
        "Notre assistant Voyage répond 24/7. Communiquez-lui le numéro de billet {numero} pour modifier votre réservation, signaler un retard ou ouvrir une réclamation.":
            "Nuestro asistente de Voyage atiende 24/7. Indíquele el número de billete {numero} para modificar su reserva, informar de un retraso o abrir una reclamación.",
        "Parler à l'assistant": "Hablar con el asistente",
        "Document personnel et non cessible · Conservez-le jusqu'à la fin de votre voyage.":
            "Documento personal e intransferible · Consérvelo hasta el final de su viaje.",
        "Voyage Assistant · Avion · Train · Bateau · Bus longue distance":
            "Voyage Assistant · Avión · Tren · Barco · Autobús de larga distancia",
        "Vous recevez cet email suite à une réservation effectuée sur notre plateforme.":
            "Recibe este correo tras una reserva realizada en nuestra plataforma.",
        "Bonjour {to_name},\n\nVotre billet est confirmé.\n\nNuméro de billet : {numero}\nTrajet : {trajet}\n\nLe billet en PDF est joint à ce message.\n\nPour toute question, communiquez le numéro de billet à notre assistant 24/7 :\n{url}\n\nBon voyage,\nVoyage Assistant":
            "Hola {to_name},\n\nSu billete está confirmado.\n\nNúmero de billete: {numero}\nTrayecto: {trajet}\n\nEl billete en PDF está adjunto a este mensaje.\n\nPara cualquier pregunta, indique el número de billete a nuestro asistente 24/7:\n{url}\n\nBuen viaje,\nVoyage Assistant",
        "Votre réclamation {numero} a bien été enregistrée":
            "Su reclamación {numero} se ha registrado correctamente",
        "Bonjour {to_name},\n\nVotre réclamation de type '{type}' a été enregistrée sous le numéro {numero}.\n\nNotre équipe vous répondra sous 72h.\n\nVoyage Assistant":
            "Hola {to_name},\n\nSu reclamación de tipo '{type}' se ha registrado con el número {numero}.\n\nNuestro equipo le responderá en un plazo de 72 h.\n\nVoyage Assistant",
    },
}


def t(s: str, lang: str = "fr", **vars) -> str:
    """Traduit `s` (clé française) vers `lang`, puis interpole les {placeholders}.

    - lang == 'fr' ou clé absente → on garde le français `s`.
    - L'interpolation est tolérante : une accolade non appariée ne fait pas planter,
      et un placeholder sans valeur correspondante est laissé tel quel.
    """
    if lang not in LANGS:
        lang = "fr"
    if lang == "fr":
        out = s
    else:
        out = TRANSLATIONS.get(lang, {}).get(s, s)
    if vars:
        for key, val in vars.items():
            out = out.replace("{" + key + "}", str(val))
    return out
