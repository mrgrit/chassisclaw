from fastapi import APIRouter, HTTPException
from app.models.asset import AssetUpsertReq

router = APIRouter()


@router.get('/assets')
def list_assets():
    return {'items': router.asset_store.list()}


@router.get('/assets/{asset_id}')
def get_asset(asset_id: str):
    asset = router.asset_store.get(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail='asset not found')
    return asset


@router.post('/assets')
def upsert_asset(req: AssetUpsertReq):
    payload = req.model_dump()
    router.asset_store.upsert(req.id, payload)
    return payload


@router.delete('/assets/{asset_id}')
def delete_asset(asset_id: str):
    deleted = router.asset_store.delete(asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='asset not found')
    return {'ok': True, 'deleted_asset_id': asset_id}
