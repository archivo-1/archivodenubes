document.addEventListener('DOMContentLoaded', function() {
    const landingPage = document.getElementById('landing-page');
    const mapContainer = document.getElementById('map-container-wrapper');
    const startButton = document.getElementById('start-map-button');
    const backButton = document.getElementById('back-to-landing-button');

    if (startButton) {
        startButton.addEventListener('click', function() {
            landingPage.classList.remove('active');
            mapContainer.classList.add('active');
            map.getView().setCenter(ol.proj.fromLonLat([-70.0, -30.0]));
            map.getView().setZoom(3);
            document.getElementById('toggle-cables').checked = true;
            document.getElementById('toggle-points').checked = true;
            document.getElementById('toggle-data-centers').checked = true;
            document.getElementById('toggle-land-cables').checked = true;

            cableLayer.setVisible(true);
            pointLayer.setVisible(true);
            dataCenterLayer.setVisible(true);
            landCableLayer.setVisible(true);
            if (map) {
                map.updateSize();
            }
        });
    }

    if (backButton) {
        backButton.addEventListener('click', function() {
            mapContainer.classList.remove('active');
            landingPage.classList.add('active');
            landingPage.scrollTo(0, 0);
        });
    }

    const map = new ol.Map({
        target: 'map',
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM(),
                className: 'ol-layer-osm-grayscale'
            })
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([-70.0, -35.0]),
            zoom: 4
        })
    });

    const interactions = map.getInteractions().getArray();
    interactions.forEach(function(interaction) {
        if (interaction instanceof ol.interaction.PinchRotate) {
            interaction.setActive(false);
        }
    });

    const glowStyle = new ol.style.Style({
        stroke: new ol.style.Stroke({
            color: 'rgba(255, 255, 255, 0.5)',
            width: 10
        }),
        image: new ol.style.Circle({
            radius: 10,
            stroke: new ol.style.Stroke({
                color: 'rgba(255, 255, 255, 0.5)',
                width: 5
            }),
            fill: new ol.style.Fill({
                color: 'rgba(255, 255, 255, 0.2)'
            })
        })
    });

    let selectedFeature = null;

    function resetFeatureStyle() {
        if (selectedFeature) {
            selectedFeature.setStyle(undefined);
            selectedFeature = null;
        }
    }

    const cableSource = new ol.source.Vector({
        format: new ol.format.GeoJSON({
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
        }),
        url: 'data/cable.geojson',
        wrapX: false
    });
    const cableLayer = new ol.layer.Vector({
        source: cableSource,
        style: function(feature) {
            const geojsonColor = feature.get('color');
            const geojsonWidth = feature.get('width');
            const geojsonLineDash = feature.get('lineDash');
            const color = geojsonColor || 'rgba(255, 0, 0, 0.7)';
            const width = geojsonWidth || 3;
            const lineDash = geojsonLineDash || undefined;
            return [
                new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: 'rgba(0, 0, 0, 0.01)',
                        width: 15
                    })
                }),
                new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: color,
                        width: width,
                        lineDash: lineDash
                    })
                })
            ];
        }
    });

    const pointSource = new ol.source.Vector({
        format: new ol.format.GeoJSON({
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
        }),
        url: 'data/puntos.geojson',
        wrapX: false
    });
    const pointLayer = new ol.layer.Vector({
        source: pointSource,
        style: function(feature) {
            const shape = feature.get('shape');
            const color = feature.get('color');
            const size = feature.get('size');
            let fillColor = color || '#FFD700';
            let strokeColor = '#333';
            let pointSize = size || 5;
            let pointStyle;
            if (shape && shape.toLowerCase() === 'circle') {
                pointStyle = new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: pointSize,
                        fill: new ol.style.Fill({
                            color: fillColor
                        }),
                        stroke: new ol.style.Stroke({
                            color: strokeColor,
                            width: 1
                        })
                    })
                });
            } else if (shape && shape.toLowerCase() === 'square') {
                pointStyle = new ol.style.Style({
                    image: new ol.style.RegularShape({
                        points: 4,
                        radius: pointSize,
                        angle: Math.PI / 4,
                        fill: new ol.style.Fill({
                            color: fillColor
                        }),
                        stroke: new ol.style.Stroke({
                            color: strokeColor,
                            width: 1
                        })
                    })
                });
            } else {
                pointStyle = new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: pointSize,
                        fill: new ol.style.Fill({
                            color: fillColor
                        }),
                        stroke: new ol.style.Stroke({
                            color: strokeColor,
                            width: 1
                        })
                    })
                });
            }
            return pointStyle;
        }
    });

    const dataCenterSource = new ol.source.Vector({
        format: new ol.format.GeoJSON({
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
        }),
        url: 'data/data_centers.geojson',
        wrapX: false
    });
    const dataCenterLayer = new ol.layer.Vector({
        source: dataCenterSource,
        style: function(feature) {
            const geometryType = feature.getGeometry().getType();
            const zoom = map.getView().getZoom();
            const color = feature.get('color');
            const size = feature.get('size');
            const shape = feature.get('shape');
            let fillColor = color || '#5DADE2';
            let strokeColor = '#333';
            let pointSize = size || 8;
            const styles = [];
            let pointGeometry = feature.getGeometry();
            if (geometryType === 'Polygon' || geometryType === 'MultiPolygon') {
                pointGeometry = ol.geom.Polygon.prototype.getInteriorPoint.call(feature.getGeometry());
            }
            let pointImage;
            if (shape && shape.toLowerCase() === 'circle') {
                pointImage = new ol.style.Circle({
                    radius: pointSize,
                    fill: new ol.style.Fill({
                        color: fillColor
                    }),
                    stroke: new ol.style.Stroke({
                        color: strokeColor,
                        width: 1
                    })
                });
            } else {
                pointImage = new ol.style.RegularShape({
                    points: 4,
                    radius: pointSize,
                    angle: Math.PI / 4,
                    fill: new ol.style.Fill({
                        color: fillColor
                    }),
                    stroke: new ol.style.Stroke({
                        color: strokeColor,
                        width: 1
                    })
                });
            }
            styles.push(new ol.style.Style({
                image: pointImage,
                geometry: pointGeometry
            }));
            if ((geometryType === 'Polygon' || geometryType === 'MultiPolygon') && zoom >= 13) {
                styles.push(new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: '#2BAB64',
                        width: 2,
                        lineDash: [10, 10]
                    })
                }));
            }
            return styles;
        }
    });

    const landCableSource = new ol.source.Vector({
        format: new ol.format.GeoJSON({
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
        }),
        url: 'data/land_cables.geojson',
        wrapX: false
    });
    const landCableLayer = new ol.layer.Vector({
        source: landCableSource,
        style: function(feature) {
            const geojsonColor = feature.get('color');
            const geojsonWidth = feature.get('width');
            const geojsonLineDash = feature.get('lineDash');
            const color = geojsonColor || 'rgba(0, 0, 255, 0.7)';
            const width = geojsonWidth || 3;
            const lineDash = geojsonLineDash || undefined;
            return new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: color,
                    width: width,
                    lineDash: lineDash
                })
            });
        }
    });

    map.addLayer(cableLayer);
    map.addLayer(landCableLayer);
    map.addLayer(pointLayer);
    map.addLayer(dataCenterLayer);

    const toggleLayerControlsButton = document.getElementById('toggle-layer-controls');
    const layerControls = document.getElementById('layer-controls');
    const infoPanel = document.getElementById('info-panel');
    const closePanelButton = document.getElementById('close-panel');
    let isClickOnFeature = false;

    toggleLayerControlsButton.addEventListener('click', () => {
        layerControls.classList.toggle('open');
        toggleLayerControlsButton.style.display = layerControls.classList.contains('open') ? 'none' : 'block';
        if (infoPanel.classList.contains('open')) {
            infoPanel.classList.remove('open');
        }
    });

    document.getElementById('toggle-cables').addEventListener('change', function() {
        cableLayer.setVisible(this.checked);
    });
    document.getElementById('toggle-points').addEventListener('change', function() {
        pointLayer.setVisible(this.checked);
    });
    document.getElementById('toggle-data-centers').addEventListener('change', function() {
        dataCenterLayer.setVisible(this.checked);
    });
    document.getElementById('toggle-land-cables').addEventListener('change', function() {
        landCableLayer.setVisible(this.checked);
    });

    document.addEventListener('click', function(event) {
        if (isClickOnFeature) {
            isClickOnFeature = false;
            return;
        }

        if (layerControls.classList.contains('open') && !layerControls.contains(event.target) && !toggleLayerControlsButton.contains(event.target)) {
            layerControls.classList.remove('open');
            toggleLayerControlsButton.style.display = 'block';
        }

        if (infoPanel.classList.contains('open') && !infoPanel.contains(event.target)) {
            infoPanel.classList.remove('open');
            resetFeatureStyle();
        }
    });

    if (infoPanel) {
        infoPanel.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    }

    if (layerControls) {
        layerControls.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    }

    const panelContent = document.getElementById('panel-content');
    const tooltip = document.getElementById('tooltip');
    const overlay = new ol.Overlay({
        element: tooltip,
        offset: [10, 0],
        positioning: 'bottom-left'
    });
    map.addOverlay(overlay);

    const translationDict = {
        'name': 'Nombre',
        'type': 'Tipo',
        'empresa': 'Empresa',
        'shape': 'Forma',
        'color': 'Color',
        'size': 'Tamaño',
        'address': 'Dirección',
        'pue': 'Eficiencia Energética (PUE)',
        'wue': 'Eficiencia Hídrica (WUE)',
        'dimensiones': 'Dimensiones Físicas',
        'tecnologias': 'Tecnologías Empleadas',
        'sistemas_refrigeracion': 'Sistemas de Refrigeración',
        'consumo_agua': 'Consumo de Agua',
        'uso_suelo': 'Uso de Suelo',
        'emisiones': 'Datos sobre Emisiones',
        'source': 'Fuente',
        'reference_link': 'Enlace de Referencia',
        'length_km': 'Longitud (km)',
        'image': 'Imagen',
        'width': 'Ancho',
        'año': 'Año',
        'consultora': 'Consultora',
        'superficie_predial': 'Superficie Predial',
        'superficie_construida': 'Superficie Construida',
        'inversion': 'Inversión',
        'tipo_de_refrigeracion': 'Tipo de Refrigeración',
        'evaluacion_ambiental': 'Evaluación Ambiental',
        'comuna': 'Comuna'
    };
    const excludedKeys = ['name', 'type', 'shape', 'color', 'size', 'opacity', 'geometry', 'width', 'lineDash', 'id'];

    function getFormattedFeatureInfo(feature) {
        const properties = feature.getProperties();
        let content = '';
        const name = properties['name'] || 'Información del Elemento';
        const type = properties['type'] || 'Elemento';
        content += `<h2>${name}</h2>`;
        content += `<h4 class="subtitle">${type}</h4>`;

        for (const key in properties) {
            const lowercaseKey = key.toLowerCase();
            if (properties.hasOwnProperty(key) && !excludedKeys.includes(lowercaseKey) && properties[key]) {
                const translatedKey = translationDict[lowercaseKey] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                let value = properties[key];

                if (lowercaseKey === 'image' && value) {
                    if (typeof value === 'string' && value.startsWith('http')) {
                        content += `<div class="info-item image-container"><img src="${value}" alt="${name}"></div>`;
                    }
                } else if (lowercaseKey === 'reference_link' && value) {
                    content += `<div class="info-item"><strong>${translatedKey}:</strong> <a href="${value}" target="_blank" rel="noopener noreferrer">Ver Referencia</a></div>`;
                } else {
                    if (value !== null && value !== undefined && value !== '') {
                        content += `<div class="info-item"><strong>${translatedKey}:</strong> ${value}</div>`;
                    }
                }
            }
        }
        return content;
    }

    closePanelButton.addEventListener('click', () => {
        infoPanel.classList.remove('open');
        resetFeatureStyle();
    });

    map.on('pointermove', function(event) {
        const feature = map.forEachFeatureAtPixel(event.pixel, function(feature) {
            return feature;
        });

        if (feature) {
            overlay.setPosition(event.coordinate);
            const featureName = feature.get('nombre') || feature.get('name') || '';
            const featureType = feature.get('type') || '';
            let tooltipContent = `<strong>${featureName}</strong>`;
            if (featureType) {
                tooltipContent += `<br>${featureType}`;
            }
            tooltip.innerHTML = tooltipContent;
            tooltip.style.textAlign = 'left';
            tooltip.style.display = 'block';
        } else {
            tooltip.style.display = 'none';
        }
    });

    map.on('click', function(evt) {
        let clickedFeature = null;
        let clickedLayer = null;
        map.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
            clickedFeature = feature;
            clickedLayer = layer;
        }, {
            hitTolerance: 5
        });

        if (clickedFeature) {
            resetFeatureStyle();
            
            selectedFeature = clickedFeature;
            
            isClickOnFeature = true;

            panelContent.innerHTML = '';
            panelContent.scrollTop = 0;
            
            panelContent.innerHTML = getFormattedFeatureInfo(selectedFeature);
            
            infoPanel.classList.add('open');
            if (layerControls.classList.contains('open')) {
                layerControls.classList.remove('open');
                if (window.innerWidth <= 768) {
                    toggleLayerControlsButton.style.display = 'block';
                }
            }

            const featureGeometry = selectedFeature.getGeometry();
            if (featureGeometry) {
                let currentMaxZoom = 16;
                const featureType = selectedFeature.get('type');

                if (featureType && (featureType.toLowerCase() === 'data center')) {
                    currentMaxZoom = 15;
                } else if (featureType && (featureType.toLowerCase() === 'punto de aterrizaje')) {
                    currentMaxZoom = 13;
                }
                
                let fitPadding = [50, 50, 50, 50];
                const mobileBreakpoint = 768;

                if (window.innerWidth <= mobileBreakpoint) {
                    fitPadding = [50, 50, infoPanel.offsetHeight + 20, 50];
                } else {
                    const panelWidth = infoPanel.offsetWidth;
                    fitPadding = [50, panelWidth + 20, 50, 50];
                }

                map.once('moveend', () => {
                    if (selectedFeature) {
                        const originalLayerStyleFunction = clickedLayer.getStyle();
                        let originalStyle = originalLayerStyleFunction(selectedFeature, map.getView().getResolution());

                        if (!Array.isArray(originalStyle)) {
                            originalStyle = [originalStyle];
                        }
                        const combinedStyles = [glowStyle, ...originalStyle];
                        selectedFeature.setStyle(combinedStyles);
                    }
                });

                map.getView().fit(featureGeometry.getExtent(), {
                    duration: 700,
                    padding: fitPadding,
                    maxZoom: currentMaxZoom
                });
            }

        } else {
            isClickOnFeature = false;
            if (infoPanel.classList.contains('open')) {
                infoPanel.classList.remove('open');
            }
            resetFeatureStyle();
        }
    });

    const searchBox = document.getElementById('search-box');
    const searchButton = document.getElementById('search-button');
    const suggestionsList = document.getElementById('suggestions-list');

    let allFeatures = [];

    function initializeSearchFeatures() {
        const layersToSearch = [pointLayer, dataCenterLayer, landCableLayer, cableLayer];
        layersToSearch.forEach(layer => {
            const source = layer.getSource();
            if (source) {
                source.on('change', function() {
                    if (source.getState() === 'ready') {
                        allFeatures.push(...source.getFeatures());
                    }
                });
                if (source.getState() === 'ready') {
                    allFeatures.push(...source.getFeatures());
                }
            }
        });
    }

    initializeSearchFeatures();

    function performSearch(searchTerm) {
        if (!searchTerm) {
            alert('Por favor, ingresa un término de búsqueda.');
            return;
        }
        
        let foundFeature = null;
        let foundLayer = null;
        
        map.getLayers().forEach(layer => {
            const source = layer.getSource();
            if (source && source instanceof ol.source.Vector) {
                const features = source.getFeatures();
                features.forEach(feature => {
                    const lowerSearchTerm = searchTerm.toLowerCase();
                    const name = feature.get('name') || feature.get('nombre');
                    const location = feature.get('location') || feature.get('ubicación');
                    const address = feature.get('address') || feature.get('Dirección');
                    const comuna = feature.get('comuna');
                    const empresa = feature.get('Empresa');
                    const operator = feature.get('operator') || feature.get('operador');
                    
                    if (
                        (name && name.toLowerCase().includes(lowerSearchTerm)) || 
                        (location && location.toLowerCase().includes(lowerSearchTerm)) ||
                        (address && address.toLowerCase().includes(lowerSearchTerm)) ||
                        (comuna && comuna.toLowerCase().includes(lowerSearchTerm)) ||
                        (empresa && empresa.toLowerCase().includes(lowerSearchTerm)) ||
                        (operator && operator.toLowerCase().includes(lowerSearchTerm))
                    ) {
                        foundFeature = feature;
                        foundLayer = layer;
                    }
                });
            }
        });

        if (foundFeature) {
            resetFeatureStyle();
            
            selectedFeature = foundFeature;
            
            isClickOnFeature = true;
            panelContent.innerHTML = '';
            panelContent.scrollTop = 0;
            
            panelContent.innerHTML = getFormattedFeatureInfo(foundFeature);
            
            infoPanel.classList.add('open');
            if (layerControls.classList.contains('open')) {
                layerControls.classList.remove('open');
                if (window.innerWidth <= 768) {
                    toggleLayerControlsButton.style.display = 'block';
                }
            }
            
            const featureGeometry = foundFeature.getGeometry();
            if (featureGeometry) {
                const view = map.getView();
                let maxZoom = 14;
                const featureType = foundFeature.get('type');

                if (featureType && (featureType.toLowerCase() === 'punto de aterrizaje')) {
                    maxZoom = 13;
                } else if (featureType && (featureType.toLowerCase() === 'data center')) {
                    maxZoom = 15;
                }

                let fitPadding = [50, 50, 50, 50];
                const mobileBreakpoint = 768;
                if (window.innerWidth <= mobileBreakpoint) {
                    fitPadding = [50, 50, infoPanel.offsetHeight + 20, 50];
                } else {
                    const panelWidth = infoPanel.offsetWidth;
                    fitPadding = [50, panelWidth + 20, 50, 50];
                }

                map.once('moveend', () => {
                    if (selectedFeature) {
                        const originalLayerStyleFunction = foundLayer.getStyle();
                        let originalStyle = originalLayerStyleFunction(selectedFeature, map.getView().getResolution());

                        if (!Array.isArray(originalStyle)) {
                            originalStyle = [originalStyle];
                        }
                        const combinedStyles = [glowStyle, ...originalStyle];
                        selectedFeature.setStyle(combinedStyles);
                    }
                });
                
                view.fit(featureGeometry.getExtent(), {
                    duration: 700,
                    padding: fitPadding,
                    maxZoom: maxZoom
                });
            }
        } else {
            const noResultsMessage = document.createElement('div');
            noResultsMessage.classList.add('no-results-message');
            noResultsMessage.textContent = 'No matches were found.';
            suggestionsList.appendChild(noResultsMessage);
            suggestionsList.style.display = 'block';
        }
    }

    searchButton.addEventListener('click', function() {
        performSearch(searchBox.value.trim());
        suggestionsList.style.display = 'none';
    });

    searchBox.addEventListener('keyup', function(event) {
        const searchTerm = searchBox.value.trim().toLowerCase();
        suggestionsList.innerHTML = '';
        const addedFeatureIds = new Set(); 

        if (searchTerm.length > 0) {
            const matchingFeatures = allFeatures.filter(feature => {
                const name = feature.get('name') || feature.get('nombre');
                const type = feature.get('type');
                const location = feature.get('location') || feature.get('ubicación');
                const address = feature.get('address') || feature.get('Dirección');
                const comuna = feature.get('comuna');
                const empresa = feature.get('Empresa');
                const operator = feature.get('operator') || feature.get('operador');

                return (
                    (name && name.toLowerCase().includes(searchTerm)) || 
                    (type && type.toLowerCase().includes(searchTerm)) ||
                    (location && location.toLowerCase().includes(searchTerm)) ||
                    (address && address.toLowerCase().includes(searchTerm)) ||
                    (comuna && comuna.toLowerCase().includes(searchTerm)) ||
                    (empresa && empresa.toLowerCase().includes(searchTerm)) ||
                    (operator && operator.toLowerCase().includes(searchTerm))
                );
            });
            if (matchingFeatures.length > 0) {
                matchingFeatures.forEach(feature => {
                    const featureId = feature.get('name') || feature.get('id');
                    if (!addedFeatureIds.has(featureId)) {
                        addedFeatureIds.add(featureId); 
                        
                        const suggestionItem = document.createElement('div');
                        suggestionItem.classList.add('suggestion-item');
                        
                        const nameSpan = document.createElement('span');
                        nameSpan.textContent = feature.get('name') || feature.get('nombre');
                        
                        const typeSpan = document.createElement('span');
                        typeSpan.classList.add('suggestion-type');
                        typeSpan.textContent = feature.get('type') || '';
                        
                        suggestionItem.appendChild(nameSpan);
                        suggestionItem.appendChild(typeSpan);

                        suggestionItem.addEventListener('click', function() {
                            searchBox.value = feature.get('name') || feature.get('nombre');
                            performSearch(searchBox.value.trim());
                            suggestionsList.style.display = 'none';
                        });
                        suggestionsList.appendChild(suggestionItem);
                    }
                });
                suggestionsList.style.display = 'block';
            } else {
                const noResultsMessage = document.createElement('div');
                noResultsMessage.classList.add('no-results-message');
                noResultsMessage.textContent = `No se encontraron resultados para "${searchTerm}".`;
                suggestionsList.appendChild(noResultsMessage);
                suggestionsList.style.display = 'block';
            }
        } else {
            suggestionsList.style.display = 'none';
        }
    });

    searchBox.addEventListener('click', function() {
        if (this.value.length > 0) {
            this.value = '';
        }
    });

    document.addEventListener('click', function(event) {
        if (!event.target.closest('.search-container')) {
            suggestionsList.style.display = 'none';
        }
    });
});
