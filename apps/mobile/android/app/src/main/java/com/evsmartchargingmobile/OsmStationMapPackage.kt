package com.evsmartchargingmobile

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager

class OsmStationMapPackage : ReactPackage {
  @Suppress("UNCHECKED_CAST")
  override fun createViewManagers(
      reactContext: ReactApplicationContext
  ): List<ViewManager<in Nothing, in Nothing>> =
      listOf(OsmStationMapViewManager()) as List<ViewManager<in Nothing, in Nothing>>
}
