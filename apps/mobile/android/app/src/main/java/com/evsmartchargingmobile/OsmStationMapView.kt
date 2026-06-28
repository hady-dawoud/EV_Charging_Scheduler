package com.evsmartchargingmobile

import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.widget.FrameLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.CustomZoomButtonsController
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker

class OsmStationMapView(context: Context) : FrameLayout(context) {
  private val mapView = MapView(context)
  private val stationMarker = Marker(mapView)

  var latitude: Double? = null
    set(value) {
      field = value
      updateStationMarker()
    }

  var longitude: Double? = null
    set(value) {
      field = value
      updateStationMarker()
    }

  var stationName: String = ""
    set(value) {
      field = value
      updateStationMarker()
    }

  var stationAddress: String = ""
    set(value) {
      field = value
      updateStationMarker()
    }

  init {
    Configuration.getInstance().userAgentValue = context.packageName

    mapView.setTileSource(TileSourceFactory.MAPNIK)
    mapView.zoomController.setVisibility(CustomZoomButtonsController.Visibility.NEVER)
    mapView.setMultiTouchControls(true)
    mapView.minZoomLevel = 3.0
    mapView.maxZoomLevel = 19.0
    mapView.controller.setZoom(STATION_ZOOM)

    addView(
        mapView,
        LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT),
    )
    addView(attributionView(), attributionLayoutParams())
  }

  override fun onAttachedToWindow() {
    super.onAttachedToWindow()
    mapView.onResume()
  }

  override fun onDetachedFromWindow() {
    mapView.onPause()
    super.onDetachedFromWindow()
  }

  private fun updateStationMarker() {
    val currentLatitude = latitude
    val currentLongitude = longitude

    if (!isValidCoordinate(currentLatitude, currentLongitude)) {
      return
    }

    val stationPoint = GeoPoint(currentLatitude!!, currentLongitude!!)
    stationMarker.position = stationPoint
    stationMarker.title = stationName
    stationMarker.subDescription = stationAddress
    stationMarker.icon = ContextCompat.getDrawable(context, R.drawable.ic_station_pin)
    stationMarker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)

    if (!mapView.overlays.contains(stationMarker)) {
      mapView.overlays.add(stationMarker)
    }

    mapView.controller.setZoom(STATION_ZOOM)
    mapView.controller.setCenter(stationPoint)
    mapView.invalidate()
  }

  private fun isValidCoordinate(latitude: Double?, longitude: Double?) =
      latitude != null &&
          longitude != null &&
          !latitude.isNaN() &&
          !latitude.isInfinite() &&
          !longitude.isNaN() &&
          !longitude.isInfinite()

  private fun attributionView() =
      TextView(context).apply {
        text = OSM_ATTRIBUTION
        setBackgroundColor(ATTRIBUTION_BACKGROUND)
        setPadding(8, 4, 8, 4)
        setTextColor(Color.WHITE)
        textSize = 10f
      }

  private fun attributionLayoutParams() =
      LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT).apply {
        gravity = Gravity.BOTTOM or Gravity.START
        leftMargin = 12
        bottomMargin = 12
      }

  companion object {
    private const val STATION_ZOOM = 16.5
    private const val OSM_ATTRIBUTION = "\u00A9 OpenStreetMap contributors"
    private const val ATTRIBUTION_BACKGROUND = 0x99000000.toInt()
  }
}
