export function Lighting() {
  return (
    <>
      <color attach="background" args={['#E8D9C4']} />
      <fog attach="fog" args={['#E4D2BA', 8, 22]} />
      <ambientLight intensity={0.45} color="#F4EEE5" />
      <directionalLight
        castShadow
        position={[4.5, 7, 3]}
        intensity={1.55}
        color="#FFE6C8"
        shadow-mapSize={[1024, 1024]}
        shadow-camera-far={20}
        shadow-camera-left={-6}
        shadow-camera-right={6}
        shadow-camera-top={6}
        shadow-camera-bottom={-6}
        shadow-bias={-0.0002}
      />
      <directionalLight position={[-3, 2.5, -2]} intensity={0.35} color="#AC624B" />
      <pointLight position={[0.2, 2.2, 1.5]} intensity={0.55} color="#FFD7A8" distance={8} />
      <hemisphereLight args={['#F7EBDD', '#8A6A55', 0.4]} />
    </>
  )
}
