import { useEffect, useRef } from 'react'
import Plyr from 'plyr'
import { usePlayer } from '../hooks/usePlayer'

export default function VideoPlayer({ src, episodeId, onEnded }) {
  const videoRef = useRef(null)
  const playerRef = useRef(null)
  const { startSaving, stopSaving } = usePlayer(episodeId)

  useEffect(() => {
    if (!videoRef.current || !src) return

    const player = new Plyr(videoRef.current, {
      controls: [
        'play-large',
        'rewind',
        'play',
        'fast-forward',
        'progress',
        'current-time',
        'duration',
        'mute',
        'volume',
        'captions',
        'settings',
        'fullscreen',
      ],
      settings: ['quality', 'speed', 'captions'],
      speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] },
      keyboard: { focused: true, global: false },
      tooltips: { controls: true, seek: true },
      captions: { active: false, language: 'pt' },
      i18n: {
        play: 'Reproduzir',
        pause: 'Pausar',
        mute: 'Silenciar',
        unmute: 'Ativar som',
        enterFullscreen: 'Tela cheia',
        exitFullscreen: 'Sair da tela cheia',
        captions: 'Legendas',
        settings: 'Configurações',
        speed: 'Velocidade',
        quality: 'Qualidade',
        normal: 'Normal',
      },
    })

    playerRef.current = player

    player.on('ready', () => {
      startSaving(() => player.currentTime)
    })

    player.on('ended', () => {
      stopSaving()
      onEnded?.()
    })

    player.on('pause', () => {
      // Position saved on next interval tick
    })

    return () => {
      stopSaving()
      player.destroy()
    }
  }, [src])

  if (!src) return null

  const isYouTube = src.includes('youtube.com') || src.includes('youtu.be')
  const isVimeo = src.includes('vimeo.com')

  if (isYouTube || isVimeo) {
    return (
      <div className="w-full max-w-5xl mx-auto">
        <div
          ref={videoRef}
          data-plyr-provider={isYouTube ? 'youtube' : 'vimeo'}
          data-plyr-embed-id={extractEmbedId(src)}
          className="w-full"
        />
      </div>
    )
  }

  return (
    <div className="w-full max-w-5xl mx-auto">
      <video
        ref={videoRef}
        className="w-full"
        src={src}
        crossOrigin="anonymous"
        playsInline
        controls={false}
      />
    </div>
  )
}

function extractEmbedId(url) {
  if (url.includes('youtube.com/watch?v=')) {
    return url.split('v=')[1]?.split('&')[0] || ''
  }
  if (url.includes('youtu.be/')) {
    return url.split('youtu.be/')[1]?.split('?')[0] || ''
  }
  if (url.includes('vimeo.com/')) {
    return url.split('vimeo.com/')[1]?.split('?')[0] || ''
  }
  return url
}
