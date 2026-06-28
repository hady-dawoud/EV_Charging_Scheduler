package com.evsmartchargingmobile

import com.facebook.react.module.annotations.ReactModule
import com.facebook.react.uimanager.SimpleViewManager
import com.facebook.react.uimanager.ThemedReactContext
import com.facebook.react.uimanager.annotations.ReactProp

@ReactModule(name = OsmStationMapViewManager.REACT_CLASS)
class OsmStationMapViewManager : SimpleViewManager<OsmStationMapView>() {
  override fun getName() = REACT_CLASS

  override fun createViewInstance(reactContext: ThemedReactContext) =
      OsmStationMapView(reactContext)

  @ReactProp(name = "latitude")
  fun setLatitude(view: OsmStationMapView, latitude: Double) {
    view.latitude = latitude
  }

  @ReactProp(name = "longitude")
  fun setLongitude(view: OsmStationMapView, longitude: Double) {
    view.longitude = longitude
  }

  @ReactProp(name = "stationName")
  fun setStationName(view: OsmStationMapView, stationName: String?) {
    view.stationName = stationName.orEmpty()
  }

  @ReactProp(name = "stationAddress")
  fun setStationAddress(view: OsmStationMapView, stationAddress: String?) {
    view.stationAddress = stationAddress.orEmpty()
  }

  companion object {
    const val REACT_CLASS = "OsmStationMapView"
  }
}
