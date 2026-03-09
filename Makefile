PORT ?= 8080

.PHONY: serve view scrape render

# Start local server and open the viewer in your browser
serve:
	@echo "Starting server at http://localhost:$(PORT)/viewer.html"
	@open "http://localhost:$(PORT)/viewer.html" &
	python3 -m http.server $(PORT)

# Open the static generated index.html directly (no server needed)
view:
	open index.html

# Run the scraper and update known_products.json
scrape:
	python3 main.py

# Regenerate the static index.html from known_products.json
render:
	python3 render.py
