from dataclasses import asdict
from pathlib import Path

import geopandas as gpd
import pandas as pd

from engine.classes import SensorType
from engine.config import AVERAGE_WALKING_SPEED_MPS
from scrapers.edintraveldata import poll_edintraveldata
from scrapers.essential_edinburgh import poll_essential_edinburgh


async def poll_all_sensors() -> gpd.GeoDataFrame:
    # TODO: get sensor descriptions from PostGIS
    sensor_descriptions = gpd.read_file(Path(__file__).parent / 'sensors.json')

    # fetch measurements (note there is caching inside these functions)
    measurements = await poll_essential_edinburgh() + await poll_edintraveldata(
        [
            sensor_dict
            for sensor_dict in sensor_descriptions.to_dict(orient='records')
            if sensor_dict['type'] == SensorType.CEC_PED_FLUX_COUNTER
        ]
    )

    # tabulate measurements
    measurements = pd.DataFrame([{**asdict(m), 'measurement_class': m.__class__.__name__} for m in measurements])

    # merge in sensor details
    measurements = measurements.merge(sensor_descriptions, left_on='sensor_name', right_on='name', how='left')

    # convert ped flux counter measurements to density assuming an average walking speed of 1.3 mps
    # TODO: reintroduce the fact that average walking speed is slightly slower at higher densities
    is_ped_flux = measurements['measurement_class'] == 'PedFluxCounterMeasurement'
    measurements.loc[is_ped_flux, 'density_pax_per_m2'] = (
        measurements.loc[is_ped_flux, 'flow_pax_per_hour']
        / 3600
        / measurements.loc[is_ped_flux, 'measurement_width_m']
        / AVERAGE_WALKING_SPEED_MPS
    )

    # discard measurements that do not fall within an OA
    measurements = measurements[~measurements['oa_code'].isna()]

    # assert all measurements have a density figure
    assert not measurements['density_pax_per_m2'].isna().any(), 'Failed to convert all measurements to density'

    return measurements
