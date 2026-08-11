// SettingsPanel Alpine component — change provider, model, endpoint, etc.

function settingsComponent() {
    return {
        open: false,
        config: {},
        status: {},
        providers: [],
        model: '',
        // Pristine baseline the drawer loaded with: the Save button stays
        // disabled until the drawer holds unsaved changes (issue #38).
        originalModel: '',
        // Staged (unsaved) changes. "Set Default" and "Set API Key" no
        // longer write to disk the moment they are clicked — they arm the
        // Save button, and the changes are persisted only when it is
        // clicked (POST /api/config/default-provider, /api/config/api-key).
        defaultChanged: false,
        pendingDefaultProvider: null,   // provider staged to become the default
        pendingApiKey: null,            // { provider, key } staged API key
        selectedProvider: '',
        saving: false,
        message: null,

        // Advanced section (per-provider): endpoint override, API type
        // (Responses/Completions) and the Responses-in-server flag.  Loaded
        // from the selected provider's entry in /api/config/providers and
        // saved per-provider via PATCH /api/config, like the model.
        endpoint: '',
        apiType: '',
        responsesInServer: false,
        // Pristine baselines for the Advanced fields (like originalModel):
        // Save stays disabled until one of them actually changes.
        originalEndpoint: '',
        originalApiType: '',
        originalResponsesInServer: false,

        // "Set API Key" modal state
        keyModalOpen: false,
        keyInput: '',
        keyReveal: false,
        keyError: null,

        // Provider variants (issue #47): create a new <provider>-<word>
        // variant or delete the one selected in the combo.
        variantName: '',           // staged new variant name
        variantError: null,

        // True while the combo shows a registered variant (as opposed to a
        // base provider).
        get selectedIsVariant() {
            const p = this.selectedProviderDetail;
            return !!(p && p.variant);
        },

        // True while the selected variant is the one the next prompt
        // resolves to (deleting it would break the running session).
        get selectedVariantInUse() {
            return !!(
                this.selectedProviderDetail &&
                this.selectedProviderDetail.effective
            );
        },

        // Register a new variant via POST /api/config/variants (the web
        // counterpart of `janito --create-variant`).  The new variant is
        // persisted in config.json and shows up in the combo right away.
        async createVariant() {
            const name = this.variantName.trim();
            if (!name) {
                this.variantError = 'Enter a variant name, e.g. alibaba-tokenplan.';
                return;
            }
            this.variantError = null;
            try {
                await Api.createVariant(name);
                this.variantName = '';
                this.message = 'Saved: created variant ' + name;
                window.dispatchEvent(new CustomEvent('config-updated'));
                await this.load();
            } catch (e) {
                this.variantError = e.message;
            }
        },

        // Delete the selected variant via DELETE /api/config/variants/{name}
        // (the web counterpart of `janito --delete-variant`).  Refuses while
        // the variant is the effective provider of the running session.
        async deleteVariant() {
            const p = this.selectedProviderDetail;
            if (!p || !p.variant) return;
            if (p.effective) {
                this.message =
                    'Delete failed: this variant is in use by the current session.';
                return;
            }
            if (!window.confirm(`Delete provider variant '${p.name}' and its configuration?`)) {
                return;
            }
            try {
                await Api.deleteVariant(p.name);
                this.message = 'Saved: deleted variant ' + p.name;
                window.dispatchEvent(new CustomEvent('config-updated'));
                await this.load();
            } catch (e) {
                this.message = 'Delete failed: ' + e.message;
            }
        },

        async toggle() {
            this.open = !this.open;
            if (this.open) await this.load();
        },

        init() {
            // The API-key field describes the provider picked in the
            // combobox, so reload it whenever the selection changes.
            this.$watch('selectedProvider', () => this.refreshStatus());
        },

        async load() {
            try {
                this.config = await Api.getConfig();
                const data = await Api.getProviders();
                this.providers = data.providers || [];
                // Keep the combo where the user left it (e.g. a non-default
                // provider they are configuring) across a save's re-baseline;
                // only default to the provider actually in use (a session-only
                // override wins over the persisted default) when nothing is
                // selected yet or the current pick left the list.
                const current = this.selectedProvider;
                this.selectedProvider =
                    this.providers.some((p) => p.name === current)
                        ? current
                        : (this.providers.find((p) => p.effective) || {}).name ||
                          this.config.provider ||
                          (this.providers.find((p) => p.active) || {}).name ||
                          '';
                // The Model field describes the SELECTED provider (the combo),
                // and saving persists it per provider — so it carries that
                // provider's own model as its VALUE: its configured model
                // first, then its built-in default.  The running server's
                // model is only a last-resort fallback (it belongs to the
                // provider in use, which may differ from the selection when a
                // non-default provider is being configured).
                this.model = this.defaultModel || this.config.model || '';
                // Same for the Advanced section: every field describes the
                // SELECTED provider.  The endpoint input carries the
                // configured override ('' = fall back to the built-in
                // endpoint); the API type is the configured override or the
                // provider's built-in default (first supported type); the
                // Responses-in-server flag is the effective value.
                this.endpoint = this.selectedProviderDetail?.endpoint || '';
                this.apiType = this.resolveApiType();
                this.responsesInServer = !!this.selectedProviderDetail?.responses_in_server;
                // Record the pristine baseline: nothing to save yet, so the
                // Save button starts (and stays) disabled until the model
                // changes, a default is staged, or an API key is staged.
                this.originalModel = this.model;
                this.originalEndpoint = this.endpoint;
                this.originalApiType = this.apiType;
                this.originalResponsesInServer = this.responsesInServer;
                this.defaultChanged = false;
                this.pendingDefaultProvider = null;
                this.pendingApiKey = null;
                this.status = await Api.getStatus(this.selectedProvider);
            } catch (e) {
                this.message = 'Failed to load settings: ' + e.message;
            }
        },

        // Refresh the API-key status for the currently selected provider
        // (falls back to the active/default provider when nothing is picked).
        async refreshStatus() {
            try {
                this.status = await Api.getStatus(this.selectedProvider);
            } catch (e) {
                // Keep the stale status visible on failure.
            }
        },

        // Called from the provider <select>'s @change: adopt the newly
        // picked provider's configured model (or its built-in default) so
        // the Model field always shows a value and describes the provider
        // being edited (keeping a model name from the previous provider
        // would make the next API call fail).  The Advanced fields follow
        // the same rule: they describe the selected provider, so they are
        // reloaded from its entry too.
        onProviderChange() {
            const p = this.providers.find((x) => x.name === this.selectedProvider);
            this.model = (p && (p.model || p.default_model)) || '';
            this.endpoint = (p && p.endpoint) || '';
            this.apiType = this.resolveApiType();
            this.responsesInServer = !!(p && p.responses_in_server);
        },

        // The effective API type for the selected provider: the configured
        // override first (``api_type``), then the provider's built-in
        // default (the first of its ``supported_api_types``) — mirrors the
        // CLI's ``resolve_api_type`` resolution.
        resolveApiType() {
            const p = this.selectedProviderDetail;
            if (!p) return '';
            return (
                p.api_type ||
                p.default_api_type ||
                (p.supported_api_types && p.supported_api_types[0]) ||
                ''
            );
        },

        // The API types the selected provider supports AND that can be used
        // right now (their optional package is installed).  Rendered as one
        // option per type in the API Type combobox.  Types whose required
        // package is missing are NOT added to the combo — they are surfaced
        // separately through unavailableApiTypes so the user sees why they
        // are missing and how to enable them.
        get supportedApiTypes() {
            const p = this.selectedProviderDetail;
            return ((p && p.api_types) || []).filter((t) => t.available).map((t) => t.type);
        },

        // The API types the selected provider supports but cannot be used
        // right now because their optional Python package is missing (e.g.
        // the native "Anthropic" API type without the `anthropic` package).
        // Shown as info under the combobox (never added to it), each entry
        // carrying the required package and an install hint.
        get unavailableApiTypes() {
            const p = this.selectedProviderDetail;
            return ((p && p.api_types) || []).filter((t) => !t.available);
        },

        // True while the selected API type is the Responses API, which is
        // the only mode where the Responses-in-server toggle is meaningful.
        get apiTypeIsResponses() {
            return this.apiType === 'Responses';
        },

        // The provider object currently selected in the combobox (or null).
        get selectedProviderDetail() {
            return (
                this.providers.find((p) => p.name === this.selectedProvider) ||
                null
            );
        },

        // The model the selected provider falls back to when the override
        // field is empty: the provider's configured model first, then its
        // built-in default (mirrors the provider switcher's resolution).
        get defaultModel() {
            const p = this.selectedProviderDetail;
            return (p && (p.model || p.default_model)) || null;
        },

        // Fallback hint for the Model field, shown only while the field is
        // empty (e.g. the user cleared it, or the provider has no default):
        // names the model the next prompt would fall back to, with a
        // "(default)" marker, instead of "(not set)".
        get modelPlaceholder() {
            return this.defaultModel ? `${this.defaultModel} (default)` : '(not set)';
        },

        // The provider currently flagged as the default (or null if the list
        // hasn't loaded yet / the default isn't in the known list).
        get defaultProviderDetail() {
            return this.providers.find((p) => p.active) || null;
        },

        // True while a non-default provider is picked and the combo sits
        // in the "not the default provider" state.
        get showSetDefault() {
            return (
                !!this.selectedProviderDetail &&
                !this.selectedProviderDetail.active
            );
        },

        // True while the combo shows the provider staged to become the
        // default (drives the "default pending" badge + Cancel button).
        get isStagedProviderSelected() {
            return (
                !!this.pendingDefaultProvider &&
                this.pendingDefaultProvider === this.selectedProvider
            );
        },

        // True while the selected provider has an API key stored, so it can
        // actually be promoted to the default (mirrors the backend guard:
        // saving without a key would be rejected with 400).
        get selectedProviderHasKey() {
            return !!(
                this.selectedProviderDetail && this.selectedProviderDetail.api_key_set
            );
        },

        // True while an API key is staged but not yet written to auth.json.
        get apiKeyChanged() {
            return !!this.pendingApiKey;
        },

        // True while the drawer holds unsaved changes: the model field
        // differs from the value it loaded with, a different provider was
        // staged as the default, an API key was staged, or one of the
        // Advanced section fields (endpoint / api type / Responses-in-server)
        // changed.  The Save button is disabled until one of these happens
        // (issue #38).
        get canSave() {
            return (
                this.model !== this.originalModel ||
                this.defaultChanged ||
                this.apiKeyChanged ||
                this.endpoint !== this.originalEndpoint ||
                this.apiType !== this.originalApiType ||
                this.responsesInServer !== this.originalResponsesInServer
            );
        },

        // Transient confirmation shown after a successful save.  (Note the
        // trailing colon — "…failed:" errors must NOT render in the green
        // confirmation style.)
        get hintMessage() {
            const confirmPrefixes = ['Saved:'];
            return this.message &&
                confirmPrefixes.some((p) => this.message.startsWith(p))
                ? this.message
                : null;
        },

        // Stage the selected provider as the new default.  Nothing is
        // written to ~/.janito/config.json here — the Save button persists
        // it (POST /api/config/default-provider) and re-baselines the
        // drawer, so the next prompt uses it — no restart needed.
        setDefaultProvider() {
            const p = this.selectedProviderDetail;
            if (!p) return;
            if (!p.api_key_set) {
                this.message = 'Set default failed: no API key is set for this provider.';
                return;
            }
            // A different provider is now staged as the default: the drawer
            // holds unsaved changes, so arm the Save button.  Also adopt the
            // provider's configured model (or its built-in default) into the
            // field so it stays in sync with what the next prompt would use
            // once saved.
            this.pendingDefaultProvider = p.name;
            this.defaultChanged = true;
            this.model = (p.model || p.default_model) || this.model;
        },

        // Discard a staged default-provider change (the drawer stays open;
        // nothing was written to disk yet).
        unstageDefault() {
            this.pendingDefaultProvider = null;
            this.defaultChanged = false;
        },

        // ---- "Set API Key" modal ----------------------------------------

        // Open the modal pre-targeted at the provider selected in the combo
        // (falling back to the default provider while nothing is picked).
        openKeyModal() {
            if (!this.selectedProvider) return;
            this.keyInput = '';
            this.keyReveal = false;
            this.keyError = null;
            this.keyModalOpen = true;
            this.$nextTick(() => {
                if (this.$refs.keyInput) this.$refs.keyInput.focus();
            });
        },

        closeKeyModal() {
            this.keyModalOpen = false;
            this.keyError = null;
            this.keyInput = '';
        },

        // Stage the typed key for the selected provider.  Nothing is written
        // to ~/.janito/auth.json here — the Save button persists it
        // (POST /api/config/api-key) and re-baselines the drawer.
        saveApiKey() {
            const key = this.keyInput.trim();
            if (!key) {
                this.keyError = 'Please paste an API key first.';
                return;
            }
            this.pendingApiKey = { provider: this.selectedProvider, key };
            this.keyModalOpen = false;
            this.keyInput = '';
        },

        // Persist every staged/edited change with one Save click: the model
        // override, the staged default provider, and the staged API key.
        async save() {
            this.saving = true;
            this.message = null;
            try {
                const saved = [];

                // 1. Promote the staged provider to the persisted default
                //    first, so the model override below lands on the
                //    provider being defaulted.
                if (this.defaultChanged && this.pendingDefaultProvider) {
                    const data = await Api.setDefaultProvider(this.pendingDefaultProvider);
                    saved.push(`default: ${data.provider}`);
                }

                // 2. Persist the model override (if the field changed).  The
                //    model is stored per provider in config.json, so send the
                //    provider the field describes — the one selected in the
                //    combo — and the backend writes it under
                //    providers.<name>.model (mirrored into the running server
                //    when it is the provider in use).
                if (this.model !== this.originalModel) {
                    const updated = await Api.patchConfig({
                        model: this.model,
                        provider: this.selectedProvider,
                    });
                    saved.push(...Object.keys(updated.updated));
                }

                // 2.5. Persist the Advanced section changes (endpoint / API
                //    type / Responses-in-server) — only the fields that
                //    actually changed, each scoped to the selected provider.
                //    An emptied endpoint or API type clears the per-provider
                //    override on the server (falls back to the built-in).
                const advancedPatch = {};
                if (this.endpoint !== this.originalEndpoint) {
                    advancedPatch.endpoint = this.endpoint;
                }
                if (this.apiType !== this.originalApiType) {
                    advancedPatch.api_type = this.apiType;
                }
                if (this.responsesInServer !== this.originalResponsesInServer) {
                    advancedPatch.responses_in_server = this.responsesInServer;
                }
                if (Object.keys(advancedPatch).length) {
                    advancedPatch.provider = this.selectedProvider;
                    const updated = await Api.patchConfig(advancedPatch);
                    saved.push(...Object.keys(updated.updated));
                }

                // 3. Store the staged API key (per-provider; independent of
                //    the default-provider change above).
                if (this.pendingApiKey) {
                    await Api.setApiKey(this.pendingApiKey.provider, this.pendingApiKey.key);
                    saved.push(`api key: ${this.pendingApiKey.provider}`);
                }

                // Reflect into the status bar / root config.
                if (this.$dispatch) {
                    this.$dispatch('config-updated', {
                        provider: this.pendingDefaultProvider,
                    });
                    this.$dispatch('janito-provider-changed', {
                        provider: this.pendingDefaultProvider,
                        model: this.model,
                    });
                }

                // Re-read the server state (new default, key status) so the
                // drawer, combo and status bar all agree again.
                try {
                    await this.load();
                } catch (e) {
                    // Non-fatal: keep the saved confirmation.
                }

                // The drawer is pristine again: disable the Save button until
                // the next edit, default stage, or key stage.  The Advanced
                // baselines are re-established from the freshly loaded
                // provider entry (the server is the source of truth after a
                // save), so saving with no changes stays a no-op.
                this.originalModel = this.model;
                this.originalEndpoint = this.endpoint;
                this.originalApiType = this.apiType;
                this.originalResponsesInServer = this.responsesInServer;
                this.defaultChanged = false;
                this.pendingDefaultProvider = null;
                this.pendingApiKey = null;
                this.message = 'Saved: ' + saved.join(', ');
                setTimeout(() => { this.message = null; }, 2500);
            } catch (e) {
                // The server may have rejected (or partially applied) the
                // changes: re-read the providers so the drawer and the
                // server agree on the true state again.
                window.dispatchEvent(new CustomEvent('config-updated'));
                this.message = 'Save failed: ' + e.message;
            } finally {
                this.saving = false;
            }
        },

        close() { this.open = false; },
    };
}
