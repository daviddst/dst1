# Sécurité DST1

## Constats prioritaires

Les constats ci-dessous proviennent du code et de la configuration versionnés ;
ils décrivent l’exposition possible, pas nécessairement l’accessibilité depuis
Internet (qui dépend du pare-feu et du réseau hôte).

1. **P1 — Actions sensibles sans verrou de confirmation technique.** Les workflows
	 déclarent `require_confirmation`, mais `tool_loader` ne transmet pas ce flag
	 dans le schéma réellement utilisé. L’endpoint texte appelle directement le
	 handler retourné par Gemini. La consigne conversationnelle de
	 `agent_config.yaml` ne constitue pas une autorisation vérifiable côté
	 serveur. Les envois, suppressions et modifications doivent être bloqués
	 côté application tant qu’une confirmation liée à l’action exacte n’a pas
	 été enregistrée.
2. **P1 — Routes Web sans authentification applicative.** `/token`, `/text-query` et
	 `/logs/stream` sont exposées par la façade ; aucun contrôle utilisateur ou
	 limitation de débit n’apparaît dans `server.py`. `/token` accepte une
	 identité et une room choisies par l’appelant. Le CORS est `*`. Ajouter une
	 authentification, une autorisation et une limitation de débit ; CORS seul
	 n’est pas une frontière de sécurité.
3. **P1 — Logs contenant des données d’action.** Le loader journalise les arguments
	 complets et les réponses n8n ; l’endpoint texte journalise aussi les
	 arguments/résultats. Le flux `/logs/stream` sert ces logs. Éviter les corps,
	 destinataires, numéros et résultats sensibles dans les logs et protéger
	 l’accès au flux.
4. **P1 — Valeurs d’authentification statiques dans Compose.** Des interfaces de
	 service utilisent des jetons codés en dur. De plus, la substitution du mot
	 de passe Tracearr est une expression opaque avec une valeur par défaut
	 prévisible. Remplacer ces valeurs par des variables explicites obligatoires
	 ou des secrets, puis renouveler les identifiants existants.
5. **P1/P2 — Ports publiés directement.** Le Compose publie notamment PostgreSQL,
	 n8n, Web, Evolution API, Redis et Whisper, ainsi que d’autres interfaces
	 d’administration. Sans adresse de liaison explicite, Docker publie en
	 général sur toutes les interfaces. Restreindre aux réseaux nécessaires et
	 vérifier les règles firewall du serveur.

## Autres risques et optimisations

- `text_endpoint.py` utilise `text:default` pour toutes les requêtes sans
	`session_id`, ce qui mélange leur contexte. La mémoire et les locks sont en
	RAM sans limite globale du nombre de sessions ni taille maximale de message.
	Une purge peut aussi retirer un lock encore détenu si une session expirée a
	une requête en cours. Utiliser des identifiants isolés, borner les entrées et
	rendre la purge compatible avec les requêtes actives.
- L’appel `client.models.generate_content` est synchrone dans une route async ;
	il peut bloquer la boucle FastAPI sous charge. Employer l’API asynchrone du
	SDK ou isoler cet appel dans un thread.
- Le script d’initialisation PostgreSQL interpole des noms de base et de rôle
	dans du SQL sans validation/quotage. Valider les identifiants ou utiliser une
	construction SQL sûre.
- `export_dst1_tools.sh` écrase la variable `N8N_API_BASE` et écrit les réponses
	API brutes directement dans le dossier versionné. Nettoyer les métadonnées
	personnelles/runtime dans un fichier temporaire avant promotion vers Git.
- `scripts/deploy/deploy.sh` utilise `rsync --delete` sur des répertoires
	entiers. Ajouter un mode dry-run et un garde-fou contre les fichiers runtime
	supplémentaires.
- Les dépendances Python et plusieurs images Docker sont flottantes (`latest`
	ou plages compatibles). Épingler les versions et mettre à jour de manière
	contrôlée pour rendre les builds reproductibles. L’interface charge aussi
	`livekit-client` depuis une URL CDN sans version ni intégrité SRI ; épingler
	l’URL et ajouter une empreinte vérifiée.
- Aucun test automatisé dédié n’est présent dans `tests/`. La validation
	actuelle compile les sources Python, parse les exports JSON et vérifie la
	configuration Compose ; elle ne teste pas les workflows ni les actions. Elle
	recherche les noms de fichiers sensibles suivis, pas les secrets codés en
	dur dans le contenu des fichiers.

## Règles de traitement des secrets

- Ne jamais lire, afficher ou versionner les fichiers `.env` réels, tokens,
	mots de passe ou credentials.
- Une clé collée dans un chat, un log ou un export doit être considérée comme
	exposée : la révoquer et en créer une nouvelle.
- Ne jamais copier les volumes n8n/PostgreSQL, logs, exécutions ou sauvegardes
	dans Git.
- Toute validation fonctionnelle d’un tool d’action doit utiliser des
	simulations ; une action externe réelle exige une autorisation distincte.
