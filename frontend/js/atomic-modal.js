/**
 * Atomic Modal for Text Labs
 * Configuration modal for atomic component types
 *
 * 5 Component Types:
 * - METRICS: Number-focused KPI cards
 * - TABLE: Grid-based data tables
 * - TEXT_BOX: Unified configurable text boxes
 * - CHART: Data visualizations (14 chart types via Analytics Service)
 * - IMAGE: AI-generated images with configurable style and position
 */

// Grid constants (Layout Service compatible)
const GRID_COLS = 32;
const GRID_ROWS = 18;
const GRID_CELL_SIZE = 60;  // pixels per grid cell

// IMAGE position presets mapping using grid-based coordinates
// Content safe zone: rows 4-17, cols 2-31
const IMAGE_POSITION_PRESETS = {
    'full':         { start_col: 2,  start_row: 4,  width: 30, height: 14 },  // Full content area
    'half-left':    { start_col: 2,  start_row: 4,  width: 15, height: 14 },  // Left half
    'half-right':   { start_col: 17, start_row: 4,  width: 15, height: 14 },  // Right half
    'quarter-tl':   { start_col: 2,  start_row: 4,  width: 15, height: 7 },   // Top left quarter
    'quarter-tr':   { start_col: 17, start_row: 4,  width: 15, height: 7 },   // Top right quarter
    'quarter-bl':   { start_col: 2,  start_row: 11, width: 15, height: 7 },   // Bottom left quarter
    'quarter-br':   { start_col: 17, start_row: 11, width: 15, height: 7 },   // Bottom right quarter
    'center-wide':  { start_col: 4,  start_row: 5,  width: 24, height: 12 },  // Center wide (approx 16:9)
    'center-square':{ start_col: 8,  start_row: 4,  width: 14, height: 14 }   // Center square (1:1)
};

// ELEMENT position presets for TEXT_BOX, METRICS, TABLE
// Simpler preset set for non-image elements
const ELEMENT_POSITION_PRESETS = {
    'full':       { start_col: 2,  start_row: 4,  width: 30, height: 14 },  // Full content area
    'half-left':  { start_col: 2,  start_row: 4,  width: 15, height: 14 },  // Left half
    'half-right': { start_col: 17, start_row: 4,  width: 15, height: 14 },  // Right half
    'center':     { start_col: 4,  start_row: 5,  width: 24, height: 10 }   // Center
};

class AtomicModal {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.backdrop = this.modal.querySelector('.modal-backdrop');
        this.form = document.getElementById('atomic-form');
        this.titleEl = document.getElementById('modal-title');
        this.closeBtn = document.getElementById('modal-close');
        this.cancelBtn = document.getElementById('modal-cancel');
        this.submitBtn = document.getElementById('modal-submit');

        // Form elements
        this.countSelect = document.getElementById('count-select');
        this.layoutSelect = document.getElementById('layout-select');
        this.itemsGroup = document.getElementById('items-group');
        this.itemsSelect = document.getElementById('items-select');
        this.tableConfig = document.getElementById('table-config');
        this.colsSelect = document.getElementById('cols-select');
        this.rowsSelect = document.getElementById('rows-select');
        this.textboxConfig = document.getElementById('textbox-config');
        this.promptInput = document.getElementById('prompt-input');

        // Current state
        this.currentType = null;
        this.onSubmitCallback = null;

        // TEXT_BOX configuration state (default values)
        // Note: color_scheme and theme_mode are hardcoded in getFormData() - not user-configurable
        this.textboxState = {
            background: 'colored',
            corners: 'rounded',
            border: 'false',
            show_title: 'true',
            title_style: 'plain',
            list_style: 'bullets',
            layout: 'horizontal',
            heading_align: 'left',
            content_align: 'left',
            placeholder_mode: 'false',
            title_min_chars: '30',
            title_max_chars: '40',
            item_min_chars: '80',
            item_max_chars: '100',
            color_variant: '',
            grid_cols: ''
        };

        // CHART configuration state (default values)
        this.chartState = {
            chart_type: 'line',
            include_insights: 'false',
            series_names: ''
        };

        // IMAGE configuration state (default values)
        // Uses grid-based positioning: start_col, start_row, width, height
        // Aspect ratio is calculated from width/height automatically
        this.imageState = {
            style: 'realistic',
            quality: 'standard',
            start_col: 2,      // Grid column (1-32)
            start_row: 4,      // Grid row (1-18)
            width: 30,         // Width in grid units (4-32)
            height: 14,        // Height in grid units (4-18)
            placeholder_mode: 'false'
        };

        // METRICS configuration state (default values)
        this.metricsState = {
            corners: 'rounded',
            border: 'false',
            alignment: 'center',
            color_scheme: 'gradient',
            layout: 'horizontal',
            placeholder_mode: 'false',
            color_variant: ''
        };

        // TABLE configuration state (default values)
        this.tableState = {
            stripe_rows: 'true',
            corners: 'square',
            header_style: 'solid',
            alignment: 'left',
            border_style: 'light',
            layout: 'horizontal',
            placeholder_mode: 'false',
            header_color: '',
            first_column_bold: 'false',
            last_column_bold: 'false',
            show_total_row: 'false',
            header_min_chars: '5',
            header_max_chars: '25',
            cell_min_chars: '10',
            cell_max_chars: '50'
        };

        // Position state for TEXT_BOX, METRICS, TABLE (grid positioning)
        this.textboxPositionState = { start_col: 2, start_row: 4, width: 28, height: 12 };
        this.metricsPositionState = { start_col: 2, start_row: 4, width: 28, height: 8 };
        this.tablePositionState = { start_col: 2, start_row: 4, width: 28, height: 10 };

        // Chart config elements
        this.chartConfig = document.getElementById('chart-config');
        this.chartTypeSelect = document.getElementById('chart-type-select');
        this.seriesNamesInput = document.getElementById('series-names-input');
        this.seriesNamesGroup = document.getElementById('series-names-group');

        // Image config elements
        this.imageConfig = document.getElementById('image-config');
        this.imageStyleSelect = document.getElementById('image-style-select');
        this.imageQualitySelect = document.getElementById('image-quality-select');
        this.imagePositionPreset = document.getElementById('image-position-preset');
        // Grid position inputs
        this.imageStartColInput = document.getElementById('image-start-col');
        this.imageStartRowInput = document.getElementById('image-start-row');
        this.imageGridWidthInput = document.getElementById('image-grid-width');
        this.imageGridHeightInput = document.getElementById('image-grid-height');
        // Calculated info display
        this.imagePixelSizeSpan = document.getElementById('image-pixel-size');
        this.imageAspectRatioSpan = document.getElementById('image-aspect-ratio');

        // Prompt group element (for show/hide with placeholder mode)
        this.promptGroup = document.getElementById('prompt-group');

        // Layout dropdown group (to hide for TEXT_BOX)
        this.layoutDropdownGroup = document.getElementById('layout-dropdown-group');

        // METRICS and TABLE styling config elements
        this.metricsConfig = document.getElementById('metrics-config');
        this.tableStylingConfig = document.getElementById('table-styling-config');

        // Position config elements (for TEXT_BOX, METRICS, TABLE)
        this.positionConfig = document.getElementById('position-config');
        this.positionPreset = document.getElementById('position-preset');
        this.positionStartCol = document.getElementById('position-start-col');
        this.positionStartRow = document.getElementById('position-start-row');
        this.positionWidth = document.getElementById('position-width');
        this.positionHeight = document.getElementById('position-height');
        this.positionPixelSize = document.getElementById('position-pixel-size');

        // Component configuration (4 types)
        this.componentConfig = {
            METRICS: {
                label: 'Metrics',
                icon: '📊',
                countRange: [1, 4],
                defaultCount: 1,
                hasItems: false,
                placeholder: 'e.g., Q4 revenue metrics showing growth, profit margin, and customer acquisition'
            },
            TABLE: {
                label: 'Table',
                icon: '▦',
                countRange: [1, 2],
                defaultCount: 1,
                hasItems: false,
                isTable: true,
                colsRange: [2, 6],
                rowsRange: [2, 10],
                defaultCols: 4,
                defaultRows: 5,
                placeholder: 'e.g., Feature comparison matrix or pricing breakdown'
            },
            TEXT_BOX: {
                label: 'Text Box',
                icon: '📝',
                countRange: [1, 6],
                defaultCount: 1,
                itemsRange: [1, 7],
                defaultItems: 4,
                itemsLabel: 'Items per box',
                isTextBox: true,
                placeholder: 'e.g., Key features and benefits of the product'
            },
            CHART: {
                label: 'Chart',
                icon: '📈',
                countRange: [1, 2],
                defaultCount: 1,
                hasItems: false,
                isChart: true,
                placeholder: 'e.g., Show quarterly revenue growth for 2024 with strong Q3-Q4 performance'
            },
            IMAGE: {
                label: 'Image',
                icon: '🖼️',
                countRange: [1, 4],
                defaultCount: 1,
                hasItems: false,
                isImage: true,
                placeholder: 'e.g., Modern office space with team collaboration, or a city skyline at sunset'
            }
        };

        this.setupEventListeners();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Close modal on backdrop click
        this.backdrop.addEventListener('click', () => this.close());

        // Close button
        this.closeBtn.addEventListener('click', () => this.close());

        // Cancel button
        this.cancelBtn.addEventListener('click', () => this.close());

        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
                this.close();
            }
        });

        // Toggle button clicks for TEXT_BOX config
        this.setupToggleButtons();

        // Chart type and options listeners
        this.setupChartEventListeners();

        // Image configuration listeners
        this.setupImageEventListeners();

        // Position configuration listeners (for TEXT_BOX, METRICS, TABLE)
        this.setupPositionEventListeners();
    }

    /**
     * Set up toggle button event listeners for all component types
     */
    setupToggleButtons() {
        const toggleButtons = this.modal.querySelectorAll('.toggle-btn');

        toggleButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const field = btn.dataset.field;
                const value = btn.dataset.value;

                // Determine which state object to update based on field prefix
                if (field.startsWith('metrics_')) {
                    // METRICS config field - strip prefix and update metricsState
                    const metricsField = field.replace('metrics_', '');
                    this.metricsState[metricsField] = value;
                    console.log('[Modal] METRICS config updated:', this.metricsState);
                } else if (field.startsWith('table_')) {
                    // TABLE config field - strip prefix and update tableState
                    const tableField = field.replace('table_', '');
                    this.tableState[tableField] = value;
                    console.log('[Modal] TABLE config updated:', this.tableState);
                } else {
                    // TEXT_BOX config field (default)
                    this.textboxState[field] = value;
                    console.log('[Modal] TEXT_BOX config updated:', this.textboxState);
                }

                // Update active class for this toggle group
                const row = btn.closest('.toggle-row');
                row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Handle placeholder_mode toggle - show/hide prompt group
                if (field === 'placeholder_mode') {
                    this.updatePromptVisibility(value === 'true');
                }

                // Handle layout toggle - show/hide grid_cols dropdown
                if (field === 'layout') {
                    const gridColsRow = document.getElementById('textbox-grid-cols-row');
                    if (gridColsRow) {
                        gridColsRow.style.display = value === 'grid' ? 'flex' : 'none';
                    }
                }
            });
        });

        // Handle grid_cols select input
        const gridColsSelect = document.getElementById('textbox-grid-cols');
        if (gridColsSelect) {
            gridColsSelect.addEventListener('change', (e) => {
                this.textboxState.grid_cols = e.target.value;
                console.log('[Modal] grid_cols updated:', e.target.value);
            });
        }

        // Handle color_variant dropdown for TEXT_BOX
        const colorVariantSelect = document.getElementById('color-variant-select');
        if (colorVariantSelect) {
            colorVariantSelect.addEventListener('change', (e) => {
                this.textboxState.color_variant = e.target.value;
                console.log('[Modal] color_variant updated:', e.target.value);
            });
        }

        // Handle color_variant dropdown for METRICS
        const metricsColorVariantSelect = document.getElementById('metrics-color-variant-select');
        if (metricsColorVariantSelect) {
            metricsColorVariantSelect.addEventListener('change', (e) => {
                this.metricsState.color_variant = e.target.value;
                console.log('[Modal] METRICS color_variant updated:', e.target.value);
            });
        }

        // Handle header_color dropdown for TABLE
        const tableHeaderColorSelect = document.getElementById('table-header-color-select');
        if (tableHeaderColorSelect) {
            tableHeaderColorSelect.addEventListener('change', (e) => {
                this.tableState.header_color = e.target.value;
                console.log('[Modal] TABLE header_color updated:', e.target.value);
            });
        }

        // Handle TABLE character limit inputs
        const tableHeaderMinCharsInput = document.getElementById('table-header-min-chars');
        const tableHeaderMaxCharsInput = document.getElementById('table-header-max-chars');
        const tableCellMinCharsInput = document.getElementById('table-cell-min-chars');
        const tableCellMaxCharsInput = document.getElementById('table-cell-max-chars');

        if (tableHeaderMinCharsInput) {
            tableHeaderMinCharsInput.addEventListener('input', (e) => {
                this.tableState.header_min_chars = e.target.value;
                console.log('[Modal] TABLE header_min_chars updated:', e.target.value);
            });
        }
        if (tableHeaderMaxCharsInput) {
            tableHeaderMaxCharsInput.addEventListener('input', (e) => {
                this.tableState.header_max_chars = e.target.value;
                console.log('[Modal] TABLE header_max_chars updated:', e.target.value);
            });
        }
        if (tableCellMinCharsInput) {
            tableCellMinCharsInput.addEventListener('input', (e) => {
                this.tableState.cell_min_chars = e.target.value;
                console.log('[Modal] TABLE cell_min_chars updated:', e.target.value);
            });
        }
        if (tableCellMaxCharsInput) {
            tableCellMaxCharsInput.addEventListener('input', (e) => {
                this.tableState.cell_max_chars = e.target.value;
                console.log('[Modal] TABLE cell_max_chars updated:', e.target.value);
            });
        }

        // Handle number inputs for char limits (min and max)
        const titleMinCharsInput = document.getElementById('title-min-chars');
        const titleMaxCharsInput = document.getElementById('title-max-chars');
        const itemMinCharsInput = document.getElementById('item-min-chars');
        const itemMaxCharsInput = document.getElementById('item-max-chars');

        if (titleMinCharsInput) {
            titleMinCharsInput.addEventListener('input', (e) => {
                this.textboxState.title_min_chars = e.target.value;
                console.log('[Modal] title_min_chars updated:', e.target.value);
            });
        }

        if (titleMaxCharsInput) {
            titleMaxCharsInput.addEventListener('input', (e) => {
                this.textboxState.title_max_chars = e.target.value;
                console.log('[Modal] title_max_chars updated:', e.target.value);
            });
        }

        if (itemMinCharsInput) {
            itemMinCharsInput.addEventListener('input', (e) => {
                this.textboxState.item_min_chars = e.target.value;
                console.log('[Modal] item_min_chars updated:', e.target.value);
            });
        }

        if (itemMaxCharsInput) {
            itemMaxCharsInput.addEventListener('input', (e) => {
                this.textboxState.item_max_chars = e.target.value;
                console.log('[Modal] item_max_chars updated:', e.target.value);
            });
        }
    }

    /**
     * Update prompt group visibility based on placeholder mode
     * @param {boolean} isPlaceholder - Whether placeholder mode is active
     */
    updatePromptVisibility(isPlaceholder) {
        if (this.promptGroup) {
            if (isPlaceholder) {
                this.promptGroup.classList.add('hidden');
            } else {
                this.promptGroup.classList.remove('hidden');
            }
        }
    }

    /**
     * Reset toggle buttons to default state
     */
    resetToggleButtons() {
        // Reset state to defaults
        // Note: color_scheme and theme_mode are hardcoded in getFormData() - not user-configurable
        this.textboxState = {
            background: 'colored',
            corners: 'rounded',
            border: 'false',
            show_title: 'true',
            title_style: 'plain',
            list_style: 'bullets',
            layout: 'horizontal',
            heading_align: 'left',
            content_align: 'left',
            placeholder_mode: 'false',
            title_min_chars: '30',
            title_max_chars: '40',
            item_min_chars: '80',
            item_max_chars: '100',
            color_variant: '',
            grid_cols: ''
        };

        // Update UI to match state (toggle buttons)
        Object.entries(this.textboxState).forEach(([field, value]) => {
            const btn = this.modal.querySelector(`.toggle-btn[data-field="${field}"][data-value="${value}"]`);
            if (btn) {
                const row = btn.closest('.toggle-row');
                row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            }
        });

        // Reset number inputs for char limits
        const titleMinCharsInput = document.getElementById('title-min-chars');
        const titleMaxCharsInput = document.getElementById('title-max-chars');
        const itemMinCharsInput = document.getElementById('item-min-chars');
        const itemMaxCharsInput = document.getElementById('item-max-chars');
        if (titleMinCharsInput) titleMinCharsInput.value = '30';
        if (titleMaxCharsInput) titleMaxCharsInput.value = '40';
        if (itemMinCharsInput) itemMinCharsInput.value = '80';
        if (itemMaxCharsInput) itemMaxCharsInput.value = '100';

        // Reset grid_cols select
        const gridColsSelect = document.getElementById('textbox-grid-cols');
        if (gridColsSelect) gridColsSelect.value = '';

        // Reset color_variant dropdown
        const colorVariantSelect = document.getElementById('color-variant-select');
        if (colorVariantSelect) colorVariantSelect.value = '';

        // Hide grid_cols row (default layout is horizontal)
        const gridColsRow = document.getElementById('textbox-grid-cols-row');
        if (gridColsRow) gridColsRow.style.display = 'none';

        // Show prompt group (default is AI Generated, not Lorem Ipsum)
        this.updatePromptVisibility(false);
    }

    /**
     * Set up chart event listeners
     */
    setupChartEventListeners() {
        // Chart type selection
        if (this.chartTypeSelect) {
            this.chartTypeSelect.addEventListener('change', (e) => {
                this.chartState.chart_type = e.target.value;
                this.updateSeriesNamesVisibility();
                console.log('[Modal] Chart type updated:', e.target.value);
            });
        }

        // Series names input
        if (this.seriesNamesInput) {
            this.seriesNamesInput.addEventListener('input', (e) => {
                this.chartState.series_names = e.target.value;
                console.log('[Modal] Series names updated:', e.target.value);
            });
        }

        // Chart include_insights toggle buttons
        const chartToggleButtons = this.modal.querySelectorAll('.toggle-btn[data-field="include_insights"]');
        chartToggleButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const value = btn.dataset.value;
                this.chartState.include_insights = value;

                // Update active class
                const row = btn.closest('.toggle-row');
                row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                console.log('[Modal] Chart include_insights updated:', value);
            });
        });
    }

    /**
     * Update series names group visibility
     * Only show for multi-series chart types
     */
    updateSeriesNamesVisibility() {
        const multiSeriesTypes = ['area_stacked', 'bar_grouped', 'bar_stacked'];
        if (this.seriesNamesGroup) {
            if (multiSeriesTypes.includes(this.chartState.chart_type)) {
                this.seriesNamesGroup.style.display = 'block';
            } else {
                this.seriesNamesGroup.style.display = 'none';
            }
        }
    }

    /**
     * Set up image event listeners
     */
    setupImageEventListeners() {
        // Image style selection
        if (this.imageStyleSelect) {
            this.imageStyleSelect.addEventListener('change', (e) => {
                this.imageState.style = e.target.value;
                console.log('[Modal] Image style updated:', e.target.value);
            });
        }

        // Image quality selection
        if (this.imageQualitySelect) {
            this.imageQualitySelect.addEventListener('change', (e) => {
                this.imageState.quality = e.target.value;
                console.log('[Modal] Image quality updated:', e.target.value);
            });
        }

        // Position preset selection (quick fill)
        if (this.imagePositionPreset) {
            this.imagePositionPreset.addEventListener('change', (e) => {
                const presetKey = e.target.value;
                if (presetKey && IMAGE_POSITION_PRESETS[presetKey]) {
                    const preset = IMAGE_POSITION_PRESETS[presetKey];
                    // Fill in the grid inputs from preset
                    this.imageState.start_col = preset.start_col;
                    this.imageState.start_row = preset.start_row;
                    this.imageState.width = preset.width;
                    this.imageState.height = preset.height;
                    // Update UI
                    this.updateImageGridInputs();
                    this.updateImageCalculatedInfo();
                }
                console.log('[Modal] Image preset applied:', presetKey);
            });
        }

        // Grid position inputs - update state and calculated info on change
        const gridInputs = [
            { el: this.imageStartColInput, field: 'start_col', min: 1, max: GRID_COLS },
            { el: this.imageStartRowInput, field: 'start_row', min: 1, max: GRID_ROWS },
            { el: this.imageGridWidthInput, field: 'width', min: 4, max: GRID_COLS },
            { el: this.imageGridHeightInput, field: 'height', min: 4, max: GRID_ROWS }
        ];

        gridInputs.forEach(({ el, field, min, max }) => {
            if (el) {
                el.addEventListener('input', (e) => {
                    let value = parseInt(e.target.value) || min;
                    // Clamp to valid range
                    value = Math.max(min, Math.min(max, value));
                    this.imageState[field] = value;
                    // Clear preset selection since user modified manually
                    if (this.imagePositionPreset) {
                        this.imagePositionPreset.value = '';
                    }
                    this.updateImageCalculatedInfo();
                    console.log(`[Modal] Image ${field} updated:`, value);
                });
            }
        });

        // Image placeholder mode toggle buttons
        const imageToggleButtons = this.modal.querySelectorAll('.toggle-btn[data-field="image_placeholder_mode"]');
        imageToggleButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const value = btn.dataset.value;
                this.imageState.placeholder_mode = value;

                // Update active class
                const row = btn.closest('.toggle-row');
                row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                console.log('[Modal] Image placeholder_mode updated:', value);
            });
        });
    }

    /**
     * Update the grid input fields from imageState
     */
    updateImageGridInputs() {
        if (this.imageStartColInput) this.imageStartColInput.value = this.imageState.start_col;
        if (this.imageStartRowInput) this.imageStartRowInput.value = this.imageState.start_row;
        if (this.imageGridWidthInput) this.imageGridWidthInput.value = this.imageState.width;
        if (this.imageGridHeightInput) this.imageGridHeightInput.value = this.imageState.height;
    }

    /**
     * Update the calculated pixel size and aspect ratio display
     */
    updateImageCalculatedInfo() {
        const pixelWidth = this.imageState.width * GRID_CELL_SIZE;
        const pixelHeight = this.imageState.height * GRID_CELL_SIZE;

        // Calculate GCD for simplified aspect ratio
        const gcd = this.calculateGCD(this.imageState.width, this.imageState.height);
        const ratioW = this.imageState.width / gcd;
        const ratioH = this.imageState.height / gcd;

        if (this.imagePixelSizeSpan) {
            this.imagePixelSizeSpan.textContent = `${pixelWidth}×${pixelHeight} px`;
        }
        if (this.imageAspectRatioSpan) {
            this.imageAspectRatioSpan.textContent = `≈ ${ratioW}:${ratioH} aspect`;
        }
    }

    /**
     * Calculate Greatest Common Divisor (Euclidean algorithm)
     */
    calculateGCD(a, b) {
        a = Math.abs(a);
        b = Math.abs(b);
        while (b > 0) {
            const temp = b;
            b = a % b;
            a = temp;
        }
        return a || 1;
    }

    /**
     * Reset image state to defaults
     */
    resetImageState() {
        // Reset to full content area preset
        this.imageState = {
            style: 'realistic',
            quality: 'standard',
            start_col: 2,
            start_row: 4,
            width: 30,
            height: 14,
            placeholder_mode: 'false'
        };

        // Reset UI elements
        if (this.imageStyleSelect) {
            this.imageStyleSelect.value = 'realistic';
        }
        if (this.imageQualitySelect) {
            this.imageQualitySelect.value = 'standard';
        }
        if (this.imagePositionPreset) {
            this.imagePositionPreset.value = '';  // No preset selected by default
        }

        // Update grid inputs and calculated info
        this.updateImageGridInputs();
        this.updateImageCalculatedInfo();

        // Reset placeholder mode toggle
        const aiBtn = this.modal.querySelector('.toggle-btn[data-field="image_placeholder_mode"][data-value="false"]');
        if (aiBtn) {
            const row = aiBtn.closest('.toggle-row');
            if (row) {
                row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                aiBtn.classList.add('active');
            }
        }
    }

    /**
     * Set up position event listeners (for TEXT_BOX, METRICS, TABLE)
     */
    setupPositionEventListeners() {
        // Position preset selection
        if (this.positionPreset) {
            this.positionPreset.addEventListener('change', (e) => {
                const presetKey = e.target.value;
                if (presetKey && ELEMENT_POSITION_PRESETS[presetKey]) {
                    const preset = ELEMENT_POSITION_PRESETS[presetKey];
                    // Update state based on current component type
                    const state = this.getCurrentPositionState();
                    if (state) {
                        state.start_col = preset.start_col;
                        state.start_row = preset.start_row;
                        state.width = preset.width;
                        state.height = preset.height;
                        // Update UI
                        this.updatePositionInputs(state);
                        this.updatePositionCalculatedInfo(state);
                    }
                }
                console.log('[Modal] Position preset applied:', presetKey);
            });
        }

        // Position input listeners
        const positionInputs = [
            { el: this.positionStartCol, field: 'start_col', min: 1, max: GRID_COLS },
            { el: this.positionStartRow, field: 'start_row', min: 1, max: GRID_ROWS },
            { el: this.positionWidth, field: 'width', min: 4, max: GRID_COLS },
            { el: this.positionHeight, field: 'height', min: 4, max: GRID_ROWS }
        ];

        positionInputs.forEach(({ el, field, min, max }) => {
            if (el) {
                el.addEventListener('input', (e) => {
                    let value = parseInt(e.target.value) || min;
                    // Clamp to valid range
                    value = Math.max(min, Math.min(max, value));

                    // Update state based on current component type
                    const state = this.getCurrentPositionState();
                    if (state) {
                        state[field] = value;
                        // Clear preset selection since user modified manually
                        if (this.positionPreset) {
                            this.positionPreset.value = '';
                        }
                        this.updatePositionCalculatedInfo(state);
                    }
                    console.log(`[Modal] Position ${field} updated:`, value);
                });
            }
        });
    }

    /**
     * Get the current position state based on component type
     */
    getCurrentPositionState() {
        if (this.currentType === 'TEXT_BOX') return this.textboxPositionState;
        if (this.currentType === 'METRICS') return this.metricsPositionState;
        if (this.currentType === 'TABLE') return this.tablePositionState;
        return null;
    }

    /**
     * Update position input fields from state
     */
    updatePositionInputs(state) {
        if (this.positionStartCol) this.positionStartCol.value = state.start_col;
        if (this.positionStartRow) this.positionStartRow.value = state.start_row;
        if (this.positionWidth) this.positionWidth.value = state.width;
        if (this.positionHeight) this.positionHeight.value = state.height;
    }

    /**
     * Update the calculated pixel size display for position
     */
    updatePositionCalculatedInfo(state) {
        const pixelWidth = state.width * GRID_CELL_SIZE;
        const pixelHeight = state.height * GRID_CELL_SIZE;

        if (this.positionPixelSize) {
            this.positionPixelSize.textContent = `${pixelWidth}×${pixelHeight} px`;
        }
    }

    /**
     * Reset position state for the given component type
     */
    resetPositionState(componentType) {
        let state;
        let defaults;

        if (componentType === 'TEXT_BOX') {
            state = this.textboxPositionState;
            defaults = { start_col: 2, start_row: 4, width: 28, height: 12 };
        } else if (componentType === 'METRICS') {
            state = this.metricsPositionState;
            defaults = { start_col: 2, start_row: 4, width: 28, height: 8 };
        } else if (componentType === 'TABLE') {
            state = this.tablePositionState;
            defaults = { start_col: 2, start_row: 4, width: 28, height: 10 };
        } else {
            return;
        }

        // Reset state to defaults
        Object.assign(state, defaults);

        // Reset UI
        if (this.positionPreset) this.positionPreset.value = '';
        this.updatePositionInputs(state);
        this.updatePositionCalculatedInfo(state);
    }

    /**
     * Reset chart state to defaults
     */
    resetChartState() {
        this.chartState = {
            chart_type: 'line',
            include_insights: 'false',
            series_names: ''
        };

        // Reset UI elements
        if (this.chartTypeSelect) {
            this.chartTypeSelect.value = 'line';
        }
        if (this.seriesNamesInput) {
            this.seriesNamesInput.value = '';
        }

        // Reset include_insights toggle
        const insightsBtn = this.modal.querySelector('.toggle-btn[data-field="include_insights"][data-value="false"]');
        if (insightsBtn) {
            const row = insightsBtn.closest('.toggle-row');
            if (row) {
                row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                insightsBtn.classList.add('active');
            }
        }

        // Update series names visibility
        this.updateSeriesNamesVisibility();
    }

    /**
     * Reset METRICS state to defaults
     */
    resetMetricsState() {
        this.metricsState = {
            corners: 'rounded',
            border: 'false',
            alignment: 'center',
            color_scheme: 'gradient',
            layout: 'horizontal',
            placeholder_mode: 'false',
            color_variant: ''
        };

        // Reset toggle buttons in metrics-config
        if (this.metricsConfig) {
            // Reset each toggle group to default
            const defaults = {
                'metrics_corners': 'rounded',
                'metrics_border': 'false',
                'metrics_alignment': 'center',
                'metrics_color_scheme': 'gradient',
                'metrics_layout': 'horizontal',
                'metrics_placeholder_mode': 'false'
            };

            Object.entries(defaults).forEach(([field, value]) => {
                const btn = this.metricsConfig.querySelector(`.toggle-btn[data-field="${field}"][data-value="${value}"]`);
                if (btn) {
                    const row = btn.closest('.toggle-row');
                    if (row) {
                        row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                    }
                }
            });
        }

        // Reset color variant dropdown
        const metricsColorVariantSelect = document.getElementById('metrics-color-variant-select');
        if (metricsColorVariantSelect) metricsColorVariantSelect.value = '';
    }

    /**
     * Reset TABLE state to defaults
     */
    resetTableState() {
        this.tableState = {
            stripe_rows: 'true',
            corners: 'square',
            header_style: 'solid',
            alignment: 'left',
            border_style: 'light',
            layout: 'horizontal',
            placeholder_mode: 'false',
            header_color: '',
            first_column_bold: 'false',
            last_column_bold: 'false',
            show_total_row: 'false',
            header_min_chars: '5',
            header_max_chars: '25',
            cell_min_chars: '10',
            cell_max_chars: '50'
        };

        // Reset toggle buttons in table-styling-config
        if (this.tableStylingConfig) {
            // Reset each toggle group to default
            const defaults = {
                'table_stripe_rows': 'true',
                'table_corners': 'square',
                'table_header_style': 'solid',
                'table_alignment': 'left',
                'table_border_style': 'light',
                'table_layout': 'horizontal',
                'table_placeholder_mode': 'false',
                'table_first_column_bold': 'false',
                'table_last_column_bold': 'false',
                'table_show_total_row': 'false'
            };

            Object.entries(defaults).forEach(([field, value]) => {
                const btn = this.tableStylingConfig.querySelector(`.toggle-btn[data-field="${field}"][data-value="${value}"]`);
                if (btn) {
                    const row = btn.closest('.toggle-row');
                    if (row) {
                        row.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                    }
                }
            });
        }

        // Reset header color dropdown
        const tableHeaderColorSelect = document.getElementById('table-header-color-select');
        if (tableHeaderColorSelect) tableHeaderColorSelect.value = '';

        // Reset character limit inputs
        const tableHeaderMinCharsInput = document.getElementById('table-header-min-chars');
        const tableHeaderMaxCharsInput = document.getElementById('table-header-max-chars');
        const tableCellMinCharsInput = document.getElementById('table-cell-min-chars');
        const tableCellMaxCharsInput = document.getElementById('table-cell-max-chars');
        if (tableHeaderMinCharsInput) tableHeaderMinCharsInput.value = '5';
        if (tableHeaderMaxCharsInput) tableHeaderMaxCharsInput.value = '25';
        if (tableCellMinCharsInput) tableCellMinCharsInput.value = '10';
        if (tableCellMaxCharsInput) tableCellMaxCharsInput.value = '50';
    }

    /**
     * Open modal for a specific component type
     * @param {string} componentType - Component type (METRICS, TABLE, TEXT_BOX, CHART)
     * @param {function} onSubmit - Callback when form is submitted
     */
    open(componentType, onSubmit) {
        const config = this.componentConfig[componentType];
        if (!config) {
            console.error('[Modal] Unknown component type:', componentType);
            return;
        }

        this.currentType = componentType;
        this.onSubmitCallback = onSubmit;

        // Set title
        this.titleEl.innerHTML = `${config.icon} Add ${config.label}`;

        // Populate count dropdown
        this.populateSelect(
            this.countSelect,
            config.countRange[0],
            config.countRange[1],
            config.defaultCount
        );

        // Handle items dropdown (for TEXT_BOX)
        if (config.itemsRange) {
            this.itemsGroup.style.display = 'flex';
            const label = this.itemsGroup.querySelector('label');
            label.textContent = config.itemsLabel || 'Items per instance';
            this.populateSelect(
                this.itemsSelect,
                config.itemsRange[0],
                config.itemsRange[1],
                config.defaultItems
            );
        } else {
            this.itemsGroup.style.display = 'none';
        }

        // Handle table configuration
        if (config.isTable) {
            this.tableConfig.style.display = 'block';
            this.populateSelect(
                this.colsSelect,
                config.colsRange[0],
                config.colsRange[1],
                config.defaultCols
            );
            this.populateSelect(
                this.rowsSelect,
                config.rowsRange[0],
                config.rowsRange[1],
                config.defaultRows
            );
        } else {
            this.tableConfig.style.display = 'none';
        }

        // Handle TEXT_BOX configuration
        if (config.isTextBox) {
            this.textboxConfig.style.display = 'block';
            this.resetToggleButtons();
            // Hide general layout dropdown (TEXT_BOX uses its own toggle)
            if (this.layoutDropdownGroup) {
                this.layoutDropdownGroup.style.display = 'none';
            }
        } else {
            this.textboxConfig.style.display = 'none';
        }

        // Handle METRICS configuration
        if (componentType === 'METRICS') {
            if (this.metricsConfig) {
                this.metricsConfig.style.display = 'block';
                this.resetMetricsState();
            }
        } else {
            if (this.metricsConfig) {
                this.metricsConfig.style.display = 'none';
            }
        }

        // Handle TABLE styling configuration
        if (config.isTable) {
            if (this.tableStylingConfig) {
                this.tableStylingConfig.style.display = 'block';
                this.resetTableState();
            }
        } else {
            if (this.tableStylingConfig) {
                this.tableStylingConfig.style.display = 'none';
            }
        }

        // Handle CHART configuration
        if (config.isChart) {
            if (this.chartConfig) {
                this.chartConfig.style.display = 'block';
            }
            this.resetChartState();
            // Hide general layout dropdown (CHART doesn't use it)
            if (this.layoutDropdownGroup) {
                this.layoutDropdownGroup.style.display = 'none';
            }
        } else {
            if (this.chartConfig) {
                this.chartConfig.style.display = 'none';
            }
        }

        // Handle IMAGE configuration
        if (config.isImage) {
            if (this.imageConfig) {
                this.imageConfig.style.display = 'block';
            }
            this.resetImageState();
            // Hide general layout dropdown (IMAGE doesn't use it)
            if (this.layoutDropdownGroup) {
                this.layoutDropdownGroup.style.display = 'none';
            }
        } else {
            if (this.imageConfig) {
                this.imageConfig.style.display = 'none';
            }
            // Show general layout dropdown for non-TextBox, non-Chart, and non-Image types
            if (!config.isTextBox && !config.isChart && this.layoutDropdownGroup) {
                this.layoutDropdownGroup.style.display = 'flex';
            }
        }

        // Handle position config for TEXT_BOX, METRICS, TABLE
        // (IMAGE has its own position config)
        if (['TEXT_BOX', 'METRICS', 'TABLE'].includes(componentType)) {
            if (this.positionConfig) {
                this.positionConfig.style.display = 'block';
            }
            this.resetPositionState(componentType);
        } else {
            if (this.positionConfig) {
                this.positionConfig.style.display = 'none';
            }
        }

        // Set placeholder text
        this.promptInput.placeholder = config.placeholder;
        this.promptInput.value = '';

        // Show modal
        this.modal.classList.remove('hidden');
        this.promptInput.focus();
    }

    /**
     * Close the modal
     */
    close() {
        this.modal.classList.add('hidden');
        this.currentType = null;
        this.onSubmitCallback = null;
    }

    /**
     * Populate a select dropdown with a range of numbers
     */
    populateSelect(selectEl, min, max, defaultValue) {
        selectEl.innerHTML = '';
        for (let i = min; i <= max; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i;
            if (i === defaultValue) {
                option.selected = true;
            }
            selectEl.appendChild(option);
        }
    }

    /**
     * Get form data
     */
    getFormData() {
        const config = this.componentConfig[this.currentType];

        const data = {
            type: this.currentType,
            count: parseInt(this.countSelect.value),
            layout: this.layoutSelect.value,
            prompt: this.promptInput.value.trim()
        };

        // Add items if applicable
        if (config.itemsRange) {
            data.itemsPerInstance = parseInt(this.itemsSelect.value);
        }

        // Add table config if applicable
        if (config.isTable) {
            data.columns = parseInt(this.colsSelect.value);
            data.rows = parseInt(this.rowsSelect.value);
        }

        // Add TEXT_BOX config if applicable
        if (config.isTextBox) {
            data.textboxConfig = {
                background: this.textboxState.background,
                corners: this.textboxState.corners,
                border: this.textboxState.border === 'true',
                show_title: this.textboxState.show_title === 'true',
                title_style: this.textboxState.title_style,
                list_style: this.textboxState.list_style,
                color_scheme: 'accent',  // Hardcoded: always use pastel backgrounds
                layout: this.textboxState.layout,
                heading_align: this.textboxState.heading_align,
                content_align: this.textboxState.content_align,
                placeholder_mode: this.textboxState.placeholder_mode === 'true',
                title_min_chars: parseInt(this.textboxState.title_min_chars),
                title_max_chars: parseInt(this.textboxState.title_max_chars),
                item_min_chars: parseInt(this.textboxState.item_min_chars),
                item_max_chars: parseInt(this.textboxState.item_max_chars),
                theme_mode: 'light',  // Hardcoded: backend handles dark/light automatically
                color_variant: this.textboxState.color_variant || null,
                grid_cols: this.textboxState.grid_cols ? parseInt(this.textboxState.grid_cols) : null
            };
        }

        // Add CHART config if applicable
        if (config.isChart) {
            const seriesNamesValue = this.chartState.series_names || '';
            data.chartConfig = {
                chart_type: this.chartState.chart_type,
                include_insights: this.chartState.include_insights === 'true',
                series_names: seriesNamesValue.split(',').map(s => s.trim()).filter(s => s)
            };
        }

        // Add IMAGE config if applicable
        if (config.isImage) {
            // Convert grid-based positioning to CSS Grid format for backend
            // grid_row = "start_row / (start_row + height)"
            // grid_column = "start_col / (start_col + width)"
            const gridRow = `${this.imageState.start_row}/${this.imageState.start_row + this.imageState.height}`;
            const gridColumn = `${this.imageState.start_col}/${this.imageState.start_col + this.imageState.width}`;

            // Calculate aspect ratio from grid dimensions
            const gcd = this.calculateGCD(this.imageState.width, this.imageState.height);
            const calculatedAspectRatio = `${this.imageState.width / gcd}:${this.imageState.height / gcd}`;

            data.imageConfig = {
                style: this.imageState.style,
                quality: this.imageState.quality,
                grid_row: gridRow,
                grid_column: gridColumn,
                // Also pass the grid-based values for precise positioning
                start_col: this.imageState.start_col,
                start_row: this.imageState.start_row,
                width: this.imageState.width,
                height: this.imageState.height,
                // Calculated aspect ratio from grid dimensions
                aspect_ratio: calculatedAspectRatio,
                placeholder_mode: this.imageState.placeholder_mode === 'true'
            };
        }

        // Add METRICS config if applicable
        if (this.currentType === 'METRICS') {
            data.metricsConfig = {
                corners: this.metricsState.corners,
                border: this.metricsState.border === 'true',
                alignment: this.metricsState.alignment,
                color_scheme: this.metricsState.color_scheme,
                layout: this.metricsState.layout,
                placeholder_mode: this.metricsState.placeholder_mode === 'true',
                color_variant: this.metricsState.color_variant || null
            };
        }

        // Add TABLE styling config if applicable
        if (config.isTable) {
            data.tableConfig = {
                stripe_rows: this.tableState.stripe_rows === 'true',
                corners: this.tableState.corners,
                header_style: this.tableState.header_style,
                alignment: this.tableState.alignment,
                border_style: this.tableState.border_style,
                layout: this.tableState.layout,
                placeholder_mode: this.tableState.placeholder_mode === 'true',
                header_color: this.tableState.header_color || null,
                first_column_bold: this.tableState.first_column_bold === 'true',
                last_column_bold: this.tableState.last_column_bold === 'true',
                show_total_row: this.tableState.show_total_row === 'true',
                header_min_chars: parseInt(this.tableState.header_min_chars),
                header_max_chars: parseInt(this.tableState.header_max_chars),
                cell_min_chars: parseInt(this.tableState.cell_min_chars),
                cell_max_chars: parseInt(this.tableState.cell_max_chars)
            };
        }

        // Add position config for TEXT_BOX, METRICS, TABLE
        // (IMAGE has its own position config in imageConfig)
        // Note: Backend expects snake_case 'position_config', not camelCase
        if (['TEXT_BOX', 'METRICS', 'TABLE'].includes(this.currentType)) {
            const posState = this.getCurrentPositionState();
            if (posState) {
                data.position_config = {
                    start_col: posState.start_col,
                    start_row: posState.start_row,
                    position_width: posState.width,
                    position_height: posState.height
                };
            }
        }

        return data;
    }

    /**
     * Handle form submission
     */
    handleSubmit() {
        const data = this.getFormData();

        // Skip prompt validation if placeholder_mode is true (Lorem Ipsum)
        const isPlaceholderMode = (data.textboxConfig && data.textboxConfig.placeholder_mode) ||
                                   (data.imageConfig && data.imageConfig.placeholder_mode);

        // METRICS, TABLE, and IMAGE (with placeholder) can work with default prompts
        const allowDefaultPrompt = ['METRICS', 'TABLE'].includes(data.type) ||
                                   (data.type === 'IMAGE' && isPlaceholderMode);

        if (!isPlaceholderMode && !allowDefaultPrompt && !data.prompt) {
            this.promptInput.focus();
            this.promptInput.classList.add('error');
            setTimeout(() => this.promptInput.classList.remove('error'), 1000);
            return;
        }

        // Set default prompts for types that support it
        // Note: Avoid word "generate" as it triggers ActionType.GENERATE instead of ADD
        if (!data.prompt) {
            if (data.type === 'TEXT_BOX' && isPlaceholderMode) {
                data.prompt = 'placeholder text boxes';
            } else if (data.type === 'METRICS') {
                data.prompt = 'Add metrics cards';
            } else if (data.type === 'TABLE') {
                data.prompt = 'Add data table';
            } else if (data.type === 'IMAGE' && isPlaceholderMode) {
                data.prompt = 'Add placeholder image';
            }
        }

        console.log('[Modal] Submitting:', data);

        if (this.onSubmitCallback) {
            this.onSubmitCallback(data);
        }

        this.close();
    }

    /**
     * Build a natural language message from form data
     */
    buildMessage(data) {
        const config = this.componentConfig[data.type];
        let message = `Add ${data.count} ${config.label.toLowerCase()}`;

        if (data.layout === 'vertical') {
            message += ' stacked vertically';
        }

        if (data.itemsPerInstance) {
            message += ` with ${data.itemsPerInstance} items each`;
        }

        if (data.columns && data.rows) {
            message += ` with ${data.columns} columns and ${data.rows} rows`;
        }

        // Add TEXT_BOX config description
        if (data.textboxConfig) {
            const cfg = data.textboxConfig;
            const parts = [];

            // Theme mode
            if (cfg.theme_mode === 'dark') parts.push('dark mode');

            // Layout
            if (cfg.layout === 'vertical') parts.push('stacked vertically');
            else if (cfg.layout === 'grid') {
                parts.push('grid layout');
                if (cfg.grid_cols) parts.push(`${cfg.grid_cols} columns`);
            }

            // Color variant
            if (cfg.color_variant) parts.push(`${cfg.color_variant} color`);

            // Heading alignment
            if (cfg.heading_align === 'center') parts.push('center-aligned headings');
            else if (cfg.heading_align === 'right') parts.push('right-aligned headings');

            // Content alignment
            if (cfg.content_align === 'center') parts.push('center-aligned content');
            else if (cfg.content_align === 'right') parts.push('right-aligned content');

            // Content source
            if (cfg.placeholder_mode) parts.push('lorem ipsum');

            // Other styling
            if (cfg.background === 'transparent') parts.push('transparent background');
            if (cfg.border) parts.push('bordered');
            if (cfg.corners === 'square') parts.push('square corners');
            if (cfg.list_style === 'numbers') parts.push('numbered list');
            else if (cfg.list_style === 'none') parts.push('plain text');
            if (!cfg.show_title) parts.push('no titles');
            else if (cfg.title_style === 'highlighted') parts.push('bold titles');
            else if (cfg.title_style === 'colored-bg') parts.push('badge titles');
            else if (cfg.title_style === 'neutral') parts.push('neutral titles');

            // Add character limits
            if (cfg.title_min_chars && cfg.title_max_chars) {
                parts.push(`title ${cfg.title_min_chars}-${cfg.title_max_chars} chars`);
            }
            if (cfg.item_min_chars && cfg.item_max_chars) {
                parts.push(`items ${cfg.item_min_chars}-${cfg.item_max_chars} chars`);
            }

            if (parts.length > 0) {
                message += ` with ${parts.join(', ')}`;
            }
        }

        // Add CHART config description
        if (data.chartConfig) {
            const cfg = data.chartConfig;
            // Use the chart type as the primary description
            const chartType = cfg.chart_type.replace(/_/g, ' ');
            message = `Add ${data.count} ${chartType} chart`;

            if (cfg.include_insights) {
                message += ' with insights';
            }
            if (cfg.series_names && cfg.series_names.length > 0) {
                message += ` with series: ${cfg.series_names.join(', ')}`;
            }
        }

        // Add IMAGE config description
        if (data.imageConfig) {
            const cfg = data.imageConfig;
            message = `Add ${data.count} ${cfg.style} image`;

            const parts = [];
            if (cfg.quality !== 'standard') parts.push(`${cfg.quality} quality`);
            if (cfg.aspect_ratio) parts.push(`${cfg.aspect_ratio} aspect`);
            if (cfg.placeholder_mode) parts.push('placeholder');

            if (parts.length > 0) {
                message += ` with ${parts.join(', ')}`;
            }
        }

        // Add METRICS config description
        if (data.metricsConfig) {
            const cfg = data.metricsConfig;
            const parts = [];

            if (cfg.theme_mode === 'dark') parts.push('dark mode');
            if (cfg.corners === 'square') parts.push('square corners');
            if (cfg.border) parts.push('bordered');
            if (cfg.alignment !== 'center') parts.push(`${cfg.alignment}-aligned`);
            if (cfg.color_scheme === 'solid') parts.push('solid colors');
            else if (cfg.color_scheme === 'accent') parts.push('pastel colors');
            if (cfg.layout === 'vertical') parts.push('stacked vertically');
            else if (cfg.layout === 'grid') parts.push('grid layout');

            if (parts.length > 0) {
                message += ` with ${parts.join(', ')}`;
            }
        }

        // Add TABLE styling config description
        if (data.tableConfig) {
            const cfg = data.tableConfig;
            const parts = [];

            // Header color (MUST be included for color styling to work)
            if (cfg.header_color) parts.push(`${cfg.header_color} header`);

            if (!cfg.stripe_rows) parts.push('no row stripes');
            if (cfg.corners === 'rounded') parts.push('rounded corners');
            if (cfg.header_style === 'pastel') parts.push('pastel header');
            else if (cfg.header_style === 'minimal') parts.push('minimal header');
            if (cfg.alignment !== 'left') parts.push(`${cfg.alignment}-aligned`);
            if (cfg.border_style === 'medium') parts.push('medium borders');
            else if (cfg.border_style === 'heavy') parts.push('heavy borders');
            else if (cfg.border_style === 'none') parts.push('no borders');
            if (cfg.layout === 'vertical') parts.push('stacked vertically');

            // Column bold options
            if (cfg.first_column_bold) parts.push('first column bold');
            if (cfg.last_column_bold) parts.push('last column bold');

            // Total row
            if (cfg.show_total_row) parts.push('total row');

            // Character limits (only include if not defaults: header 5-25, cell 10-50)
            if (cfg.header_min_chars && cfg.header_max_chars &&
                (cfg.header_min_chars !== 5 || cfg.header_max_chars !== 25)) {
                parts.push(`header ${cfg.header_min_chars}-${cfg.header_max_chars} chars`);
            }
            if (cfg.cell_min_chars && cfg.cell_max_chars &&
                (cfg.cell_min_chars !== 10 || cfg.cell_max_chars !== 50)) {
                parts.push(`cell ${cfg.cell_min_chars}-${cfg.cell_max_chars} chars`);
            }

            if (parts.length > 0) {
                message += ` with ${parts.join(', ')}`;
            }
        }

        message += `: ${data.prompt}`;

        return message;
    }
}

// Export as global
window.AtomicModal = AtomicModal;
