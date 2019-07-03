import 'ol/ol.css';
import TileLayer from 'ol/layer/Tile';
import OSM from 'ol/source/OSM';
import Map from 'ol/Map.js';
import View from 'ol/View.js';
import MVT from 'ol/format/MVT.js';
import VectorTileLayer from 'ol/layer/VectorTile.js';
import VectorTileSource from 'ol/source/VectorTile.js';
import {Fill, Stroke, Style} from 'ol/style.js';

var vtLayer = new VectorTileLayer({
  declutter: false,
  source: new VectorTileSource({
    format: new MVT(),
    url: 'http://localhost:8080/{z}/{x}/{y}.pbf'
  }),
  style: new Style({
      stroke: new Stroke({
        color: 'gray',
        width: 3
      })
  })
});

var tLayer = new TileLayer({
      source: new OSM()
    });

var esriLayer = new VectorTileLayer({
  source: new VectorTileSource({
    format: new MVT(),
    url: 'https://basemaps.arcgis.com/v1/arcgis/rest/services/World_Basemap/VectorTileServer/tile/{z}/{y}/{x}.pbf'
  })
});

const map = new Map({
  target: 'map',
  layers: [
    esriLayer,
    vtLayer
  ],
  view: new View({
    center: [-8235139, 4968614],
    zoom: 14
  })
});

