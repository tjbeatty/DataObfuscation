TARGETS := install build update lint stop clean
.PHONY: $(TARGETS)
$(TARGETS):
	@echo -e "	$(RED)$@$(NC) not implemented in this repository"
