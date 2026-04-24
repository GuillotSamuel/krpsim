PYTHON		= python3
KRPSIM		= src/krpsim.py
VERIF		= src/krpsim_verif.py
TRACE		= traces/simulation_trace.txt

RESOURCES	= resources/simple resources/farm resources/ikea \
			  resources/inception resources/logistics resources/mine \
			  resources/pomme resources/recre resources/steak resources/workshop

DELAY		?= 100
FILE		?= resources/simple

.PHONY: all run test verif clean fclean re help

all: run

run:
	@echo "==> krpsim: $(FILE) (delay=$(DELAY))"
	@cd src && $(PYTHON) krpsim.py ../$(FILE) $(DELAY)

test:
	@for f in $(RESOURCES); do \
		echo "==> $$f"; \
		cd src && $(PYTHON) krpsim.py ../$$f $(DELAY); cd ..; \
		echo ""; \
	done

verif:
	@echo "==> krpsim_verif: $(FILE) / $(TRACE)"
	@cd src && $(PYTHON) krpsim_verif.py ../$(FILE) ../$(TRACE)

clean:
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	@find . -name "*.pyc" -delete 2>/dev/null; true
	@echo "Cleaned."

fclean: clean
	@rm -f $(TRACE)

re: fclean run

help:
	@echo "Usage:"
	@echo "  make run   [FILE=resources/...] [DELAY=100]  -- lance krpsim"
	@echo "  make test  [DELAY=100]                       -- lance krpsim sur toutes les ressources"
	@echo "  make verif [FILE=resources/...] [TRACE=...]  -- verifie une trace"
	@echo "  make clean                                    -- supprime les __pycache__"
	@echo "  make fclean                                   -- clean + supprime la trace"
	@echo "  make re                                       -- fclean + run"
