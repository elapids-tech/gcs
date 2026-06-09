import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { EXRLoader } from 'three/examples/jsm/loaders/EXRLoader.js';

const API_BASE_URL = 'http://localhost:8003';

const normalizeFileName = (value: string) => {
  const trimmed = value.trim().replace(/^"(.*)"$/, '$1');
  const withoutPrefix = trimmed.replace(/^\.\//, '');
  return withoutPrefix.split(/[\\/]/).pop() ?? withoutPrefix;
};

const getFileExtension = (fileName: string) => {
  const normalized = normalizeFileName(fileName);
  const dotIndex = normalized.lastIndexOf('.');
  if (dotIndex < 0) return '';
  return normalized.slice(dotIndex).toLowerCase();
};

const supportedTextureExtensions = new Set(['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.exr']);

const parseMapKdByMaterial = (mtlText: string) => {
  const mapKdByMaterial = new Map<string, string>();
  let currentMaterialName = '';

  mtlText.split(/\r?\n/).forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) return;

    if (line.startsWith('newmtl ')) {
      currentMaterialName = line.slice(7).trim();
      return;
    }

    if (!currentMaterialName || !line.startsWith('map_Kd ')) return;

    const mapDefinition = line.slice(7).trim();
    const tokens = mapDefinition.match(/(?:[^\s"]+|"[^"]*")+/g) ?? [];
    const texturePath = tokens[tokens.length - 1];
    if (texturePath) {
      mapKdByMaterial.set(currentMaterialName, normalizeFileName(texturePath));
    }
  });

  return mapKdByMaterial;
};

const ensurePlanarUv = (geometry: THREE.BufferGeometry) => {
  const existingUv = geometry.getAttribute('uv');
  if (existingUv && existingUv.count > 0) {
    return false;
  }

  const position = geometry.getAttribute('position');
  if (!position) {
    return false;
  }

  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) {
    return false;
  }

  const size = new THREE.Vector3();
  box.getSize(size);

  const minValues = [box.min.x, box.min.y, box.min.z];
  const sizeValues = [size.x, size.y, size.z];
  const axisIndices = [0, 1, 2].sort((a, b) => sizeValues[b] - sizeValues[a]);
  const uAxis = axisIndices[0];
  const vAxis = axisIndices[1];
  const rangeU = sizeValues[uAxis] > 0 ? sizeValues[uAxis] : 1;
  const rangeV = sizeValues[vAxis] > 0 ? sizeValues[vAxis] : 1;

  const uvArray = new Float32Array(position.count * 2);
  for (let i = 0; i < position.count; i += 1) {
    const coords = [position.getX(i), position.getY(i), position.getZ(i)];
    uvArray[i * 2] = (coords[uAxis] - minValues[uAxis]) / rangeU;
    uvArray[i * 2 + 1] = (coords[vAxis] - minValues[vAxis]) / rangeV;
  }

  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvArray, 2));
  geometry.attributes.uv.needsUpdate = true;
  return true;
};

const toDisplayByte = (value: number) => {
  const safe = Number.isFinite(value) && value > 0 ? value : 0;
  // Lift exposure so imported EXR textures are not rendered too dark as diffuse maps.
  const exposed = safe * 2.4;
  const clamped = Math.min(exposed, 1);
  const gammaCorrected = Math.pow(clamped, 1 / 2.2);
  return Math.max(0, Math.min(255, Math.round(gammaCorrected * 255)));
};

const readHdrChannel = (buffer: ArrayLike<number>, index: number) => {
  const raw = Number(buffer[index] ?? 0);
  if (!Number.isFinite(raw)) return 0;

  if (buffer instanceof Uint16Array) {
    return THREE.DataUtils.fromHalfFloat(raw);
  }

  return raw;
};

const convertExrToDiffuseTexture = (texture: THREE.Texture) => {
  const hdrTexture = texture as THREE.DataTexture & {
    image?: { data?: ArrayLike<number>; width?: number; height?: number };
  };
  const image = hdrTexture.image;
  const sourceData = image?.data;
  const width = image?.width ?? 0;
  const height = image?.height ?? 0;
  if (!sourceData || width <= 0 || height <= 0) {
    return null;
  }

  const pixelCount = width * height;
  const itemSize = pixelCount > 0 ? Math.floor(sourceData.length / pixelCount) : 0;
  if (itemSize < 3) {
    return null;
  }

  const ldr = new Uint8Array(pixelCount * 4);
  for (let i = 0; i < pixelCount; i += 1) {
    const srcBase = i * itemSize;
    const dstBase = i * 4;

    const r = readHdrChannel(sourceData, srcBase);
    const g = readHdrChannel(sourceData, srcBase + 1);
    const b = readHdrChannel(sourceData, srcBase + 2);

    ldr[dstBase] = toDisplayByte(r);
    ldr[dstBase + 1] = toDisplayByte(g);
    ldr[dstBase + 2] = toDisplayByte(b);
    ldr[dstBase + 3] = 255;
  }

  const diffuseTexture = new THREE.DataTexture(ldr, width, height, THREE.RGBAFormat, THREE.UnsignedByteType);
  diffuseTexture.colorSpace = THREE.SRGBColorSpace;
  diffuseTexture.flipY = hdrTexture.flipY;
  diffuseTexture.wrapS = hdrTexture.wrapS;
  diffuseTexture.wrapT = hdrTexture.wrapT;
  diffuseTexture.magFilter = THREE.LinearFilter;
  diffuseTexture.minFilter = THREE.LinearMipmapLinearFilter;
  diffuseTexture.generateMipmaps = true;
  diffuseTexture.needsUpdate = true;

  return diffuseTexture;
};

const brightenMaterialForDiffuseMap = (material: THREE.Material) => {
  const materialWithColor = material as THREE.Material & { color?: THREE.Color };
  if (materialWithColor.color) {
    // map_Kd should represent albedo color; avoid extra darkening by Kd multipliers.
    materialWithColor.color.setRGB(1, 1, 1);
  }

  const pbrMaterial = material as THREE.Material & { metalness?: number; roughness?: number };
  if (typeof pbrMaterial.metalness === 'number') {
    pbrMaterial.metalness = 0;
  }
  if (typeof pbrMaterial.roughness === 'number') {
    pbrMaterial.roughness = Math.max(pbrMaterial.roughness, 0.85);
  }
};

const convertImportedObjectToZUp = (object: THREE.Object3D) => {
  // Convert drone-like Z-down model orientation to viewer Z-up without mirror artifacts.
  object.rotateX(Math.PI);
  object.updateMatrixWorld(true);
};

type FlightAreaPageProps = {
  onModelImported: (object: THREE.Group, environmentMap: THREE.Texture | null) => void;
};

const FlightAreaPage: React.FC<FlightAreaPageProps> = ({ onModelImported }) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const activeObjectUrlsRef = useRef<string[]>([]);
  const [sfmIp, setSfmIp] = useState('');
  const [sfmPort, setSfmPort] = useState('');
  const [checkStatus, setCheckStatus] = useState<'idle' | 'checking' | 'ok' | 'error'>('idle');
  const [checkMessage, setCheckMessage] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importMessage, setImportMessage] = useState('No model loaded');

  const pageStyle: React.CSSProperties = {
    padding: '0px 10px',
    boxSizing: 'border-box',
  };

  const controlStyle: React.CSSProperties = {
    height: 24,
    padding: '0 8px',
    fontSize: 12,
    lineHeight: '24px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxSizing: 'border-box',
  };

  const projectLabelWidth = 120;
  const projectControlWidth = 220;

  const labelTextStyle: React.CSSProperties = {
    width: projectLabelWidth,
    whiteSpace: 'nowrap',
  };

  const projectRowStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: `${projectLabelWidth}px ${projectControlWidth}px auto`,
    columnGap: 12,
    alignItems: 'center',
    marginTop: 8,
  };

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/app-setting/network/flight-area-build-server`);
        const data = await res.json().catch(() => null);
        if (res.ok && data?.status === 'ok') {
          setSfmIp(String(data?.ip ?? ''));
          setSfmPort(String(data?.port ?? ''));
        }
      } catch {
        // Ignore load errors.
      }
    };
    loadSettings();
  }, []);

  const releaseActiveObjectUrls = () => {
    activeObjectUrlsRef.current.forEach((url) => {
      URL.revokeObjectURL(url);
    });
    activeObjectUrlsRef.current = [];
  };

  useEffect(() => {
    return () => {
      releaseActiveObjectUrls();
    };
  }, []);

  useEffect(() => {
    if (!folderInputRef.current) return;

    // Configure folder picking without relying on non-standard TS props in JSX.
    folderInputRef.current.setAttribute('webkitdirectory', '');
    folderInputRef.current.setAttribute('directory', '');
  }, []);

  const handleOpenImportDialog = () => {
    fileInputRef.current?.click();
  };

  const handleOpenImportFolderDialog = () => {
    folderInputRef.current?.click();
  };

  const handleImportFiles = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = '';

    if (files.length === 0) return;

    const objFile = files.find((file) => file.name.toLowerCase().endsWith('.obj'));
    if (!objFile) {
      setImportMessage('OBJ file is required.');
      return;
    }

    setIsImporting(true);
    setImportMessage('Importing files...');

    releaseActiveObjectUrls();

    const mtlFile = files.find((file) => file.name.toLowerCase().endsWith('.mtl'));
    const selectedTextureFiles = files.filter((file) => supportedTextureExtensions.has(getFileExtension(file.name)));

    const objectUrlByName = new Map<string, string>();
    const objectUrlByLowerName = new Map<string, string>();
    files.forEach((file) => {
      const objectUrl = URL.createObjectURL(file);
      objectUrlByName.set(file.name, objectUrl);
      objectUrlByLowerName.set(file.name.toLowerCase(), objectUrl);
    });

    const revokeCurrentObjectUrls = () => {
      objectUrlByName.forEach((url) => {
        URL.revokeObjectURL(url);
      });
    };

    let importSucceeded = false;

    try {
      const manager = new THREE.LoadingManager();
      const exrLoader = new EXRLoader(manager);
      manager.addHandler(/\.exr$/i, exrLoader);

      manager.setURLModifier((url) => {
        const normalized = normalizeFileName(decodeURIComponent(url));

        const byName = objectUrlByName.get(normalized);
        if (byName) {
          return byName;
        }

        const matchedUrl = objectUrlByLowerName.get(normalized.toLowerCase()) ?? null;
        if (matchedUrl) {
          return matchedUrl;
        }

        return url;
      });

      let materialCreator: MTLLoader.MaterialCreator | null = null;
      let mapKdByMaterial = new Map<string, string>();
      if (mtlFile) {
        mapKdByMaterial = parseMapKdByMaterial(await mtlFile.text());
        const mtlUrl = objectUrlByName.get(mtlFile.name);
        if (mtlUrl) {
          const mtlLoader = new MTLLoader(manager);
          materialCreator = await mtlLoader.loadAsync(mtlUrl);
          materialCreator.preload();
        }
      }

        const hdrTextureByLowerName = new Map<string, THREE.Texture>();
        const diffuseTextureByLowerName = new Map<string, THREE.Texture>();
      let convertedExrCount = 0;

      const referencedTextureNames = Array.from(new Set(Array.from(mapKdByMaterial.values()).map((name) => normalizeFileName(name))));
      const missingTextureNames = new Set<string>();

        referencedTextureNames.forEach((textureName) => {
          const lowerName = textureName.toLowerCase();
          const textureUrl = objectUrlByLowerName.get(lowerName) ?? objectUrlByName.get(textureName);
          if (!textureUrl) {
            missingTextureNames.add(textureName);
          }
        });

        const referencedExrNames = Array.from(new Set(
          Array.from(mapKdByMaterial.values()).filter((name) => getFileExtension(name) === '.exr')
        ));

        if (referencedExrNames.length > 0) {
          await Promise.all(
            referencedExrNames.map(async (textureName) => {
              const lowerName = normalizeFileName(textureName).toLowerCase();
              const textureUrl = objectUrlByLowerName.get(lowerName) ?? objectUrlByName.get(textureName);
              if (!textureUrl) {
                missingTextureNames.add(textureName);
                return;
              }

              try {
                const exrTexture = await exrLoader.loadAsync(textureUrl);
                exrTexture.name = textureName;
                exrTexture.colorSpace = THREE.LinearSRGBColorSpace;
                exrTexture.needsUpdate = true;
                hdrTextureByLowerName.set(lowerName, exrTexture);

                const diffuseTexture = convertExrToDiffuseTexture(exrTexture);
                if (diffuseTexture) {
                  diffuseTexture.name = textureName;
                  diffuseTextureByLowerName.set(lowerName, diffuseTexture);
                  convertedExrCount += 1;
                } else {
                  diffuseTextureByLowerName.set(lowerName, exrTexture);
                }
              } catch {
                missingTextureNames.add(textureName);
              }
            })
          );
        }

      if (materialCreator && mapKdByMaterial.size > 0) {
        const materialsByName = (materialCreator as unknown as { materials?: Record<string, THREE.Material> }).materials;

        mapKdByMaterial.forEach((mapKdTextureName, materialName) => {
            const extension = getFileExtension(mapKdTextureName);
            if (extension !== '.exr') {
              return;
            }

            const texture = diffuseTextureByLowerName.get(mapKdTextureName.toLowerCase());
            if (!texture) {
              missingTextureNames.add(mapKdTextureName);
              return;
            }

            const material = materialsByName?.[materialName];
            if (!material) return;

            const materialWithMap = material as THREE.Material & { map?: THREE.Texture | null };
            if ('map' in materialWithMap) {
              materialWithMap.map = texture;
              brightenMaterialForDiffuseMap(material);
              materialWithMap.needsUpdate = true;
            }
        });
      }

      const objUrl = objectUrlByName.get(objFile.name);
      if (!objUrl) {
        throw new Error('Unable to resolve OBJ file URL.');
      }

      const objLoader = new OBJLoader(manager);
      if (materialCreator) {
        objLoader.setMaterials(materialCreator);
      }

      const loadedObject = await objLoader.loadAsync(objUrl);
      convertImportedObjectToZUp(loadedObject);

        let hasUvCoordinates = false;
        let mappedMaterialCount = 0;
      loadedObject.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (!mesh.isMesh) return;

        const geometry = mesh.geometry as THREE.BufferGeometry;
        const uvAttribute = geometry?.getAttribute('uv');
        if (uvAttribute && uvAttribute.count > 0) {
          hasUvCoordinates = true;
        }

        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        materials.forEach((material) => {
          if (!material || !(material instanceof THREE.Material)) return;

          const materialName = material.name?.trim();
          const mapKdTextureName = materialName ? mapKdByMaterial.get(materialName) : undefined;
          if (!mapKdTextureName) return;

          const materialWithMap = material as THREE.Material & { map?: THREE.Texture | null };
          const hasMappedTexture = !!materialWithMap.map;

          const extension = getFileExtension(mapKdTextureName);
          if (extension === '.exr' && !hasMappedTexture) {
            const texture = diffuseTextureByLowerName.get(mapKdTextureName.toLowerCase());
            if (texture && 'map' in materialWithMap) {
              materialWithMap.map = texture;
              materialWithMap.needsUpdate = true;
            }
          }

          if (materialWithMap.map) {
            brightenMaterialForDiffuseMap(material);
            materialWithMap.needsUpdate = true;
            mappedMaterialCount += 1;
          } else {
            missingTextureNames.add(mapKdTextureName);
          }
        });
      });

      let loadedEnvironmentMap: THREE.Texture | null = null;
      const firstHdrTexture = Array.from(hdrTextureByLowerName.values())[0];
      if (firstHdrTexture) {
        const environmentTexture = firstHdrTexture.clone();
        environmentTexture.mapping = THREE.EquirectangularReflectionMapping;
        environmentTexture.needsUpdate = true;
        loadedEnvironmentMap = environmentTexture;
      }

      onModelImported(loadedObject, loadedEnvironmentMap);
      activeObjectUrlsRef.current = Array.from(objectUrlByName.values());
      importSucceeded = true;

      const importedFiles = [objFile.name, mtlFile?.name, ...selectedTextureFiles.map((file) => file.name)].filter(Boolean).join(', ');
      if (!mtlFile && selectedTextureFiles.length === 0) {
        setImportMessage('Imported OBJ only. Browser cannot auto-read sibling files; use Import Folder or select OBJ+MTL+texture files together.');
      } else if (!mtlFile) {
        setImportMessage('Imported without MTL. Select .mtl together to use map_Kd textures.');
      } else if (mapKdByMaterial.size > 0 && diffuseTextureByLowerName.size === 0) {
        setImportMessage('Imported without referenced textures. Select all files referenced by map_Kd.');
      } else if (diffuseTextureByLowerName.size > 0 && !hasUvCoordinates) {
        setImportMessage('Imported: OBJ has no UV (vt). Texture mapping is unavailable.');
      } else if (missingTextureNames.size > 0) {
        setImportMessage(`Imported with missing textures: ${Array.from(missingTextureNames).join(', ')}`);
        } else if (diffuseTextureByLowerName.size > 0 && mappedMaterialCount === 0) {
        setImportMessage('Imported, but no material map was applied. Check usemtl/map_Kd names.');
      } else {
        const conversionSummary = convertedExrCount > 0 ? `, exrLdr: ${convertedExrCount}` : '';
        const mappingSummary = diffuseTextureByLowerName.size > 0
            ? ` (mapped: ${mappedMaterialCount}, textures: ${diffuseTextureByLowerName.size}${conversionSummary})`
          : '';
        setImportMessage(`Imported: ${importedFiles}${mappingSummary}`);
      }
    } catch (error) {
      setImportMessage(error instanceof Error ? error.message : 'Failed to import model files.');
    } finally {
      setIsImporting(false);
      if (!importSucceeded) {
        revokeCurrentObjectUrls();
      }
    }
  };

  return (
    <div className="config-panel" style={pageStyle}>
      <h2>Project Management</h2>
      <div style={{ maxWidth: 480 }}>
        <h3>Server Setting</h3>
        <div style={{ display: 'flex', gap: 20, justifyContent: 'flex-start', alignItems: 'center' }}>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span>IP</span>
            <input
              type="text"
              placeholder="127.0.0.1"
              value={sfmIp}
              onChange={(e) => setSfmIp(e.target.value)}
              style={controlStyle}
            />
          </label>

          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span>Port</span>
              <input
                type="number"
                placeholder="8000"
                value={sfmPort}
                onChange={(e) => setSfmPort(e.target.value)}
                min={1}
                max={65535}
                style={controlStyle}
              />
            </label>
            <button
              type="button"
              onClick={async () => {
                const ip = sfmIp.trim();
                const port = sfmPort.trim();
                if (!ip || !port) {
                  setCheckStatus('error');
                  setCheckMessage('IP and Port required');
                  return;
                }

                setCheckStatus('checking');
                setCheckMessage('Checking...');
                try {
                  const query = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
                  const res = await fetch(`${API_BASE_URL}/flight-area/check-connection?${query}`, {
                    method: 'POST',
                  });
                  const data = await res.json().catch(() => null);
                  if (res.ok && data?.reachable) {
                    setCheckStatus('ok');
                    setCheckMessage('OK');
                  } else {
                    setCheckStatus('error');
                    setCheckMessage(data?.message || `Failed (${res.status})`);
                  }
                } catch (err) {
                  setCheckStatus('error');
                  setCheckMessage('Cannot reach backend');
                }
              }}
              disabled={checkStatus === 'checking'}
              style={controlStyle}
            >
              Check
            </button>
            <span
              aria-live="polite"
              style={{
                minWidth: 100,
                color: checkStatus === 'ok' ? '#1b7f2a' : checkStatus === 'error' ? '#b00020' : '#666',
              }}
            >
              {checkMessage}
            </span>
            <button
              type="button"
              onClick={async () => {
                const ip = sfmIp.trim();
                const port = sfmPort.trim();
                if (!ip || !port) {
                  return;
                }

                const query = `ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`;
                await fetch(`${API_BASE_URL}/app-setting/network/flight-area-build-server?${query}`, {
                  method: 'POST',
                });
              }}
              style={controlStyle}
            >
              Save
            </button>
          </div>
        </div>
        <h3>Project</h3>
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Create Project</span>
          <input
            type="text"
            placeholder="Enter the project name."
            style={{ ...controlStyle, width: projectControlWidth }}
          />
          <button type="button" style={controlStyle}>
            Create
          </button>
        </div>
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Select Project</span>
          <select defaultValue="" style={{ ...controlStyle, width: projectControlWidth }}>
            <option value="" disabled>
              -- Select a Project --
            </option>
          </select>
          <span />
        </div>
        <div style={{ borderTop: '1px solid #ddd', margin: '8px 0' }} />
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Build</span>
          <span />
          <button type="button" style={controlStyle}>
            Run
          </button>
        </div>
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Import Model</span>
          <div style={{ display: 'flex', gap: 8, width: projectControlWidth }}>
            <button
              type="button"
              onClick={handleOpenImportDialog}
              disabled={isImporting}
              style={{ ...controlStyle, flex: 1 }}
            >
              {isImporting ? 'Importing...' : 'Import Files'}
            </button>
            <button
              type="button"
              onClick={handleOpenImportFolderDialog}
              disabled={isImporting}
              style={{ ...controlStyle, flex: 1 }}
            >
              {isImporting ? 'Importing...' : 'Import Folder'}
            </button>
          </div>
          <span aria-live="polite" style={{ color: '#444', fontSize: 12 }}>
            {importMessage}
          </span>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".obj,.mtl,.exr,.png,.jpg,.jpeg,.webp"
          multiple
          onChange={handleImportFiles}
          style={{ display: 'none' }}
        />
        <input
          ref={folderInputRef}
          type="file"
          multiple
          onChange={handleImportFiles}
          style={{ display: 'none' }}
        />
        <div style={projectRowStyle}>
          <span style={labelTextStyle}>Meshroom Process State</span>
          <span style={{ ...controlStyle, width: projectControlWidth, justifyContent: 'flex-start' }} />
          <span />
        </div>
      </div>
    </div>
  );
};

export default FlightAreaPage;
