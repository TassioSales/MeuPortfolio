'use client'

import { useState, useEffect } from 'react'
import { X, Eye, EyeOff, ExternalLink, CheckCircle2, Key, ChevronRight } from 'lucide-react'
import { getMistralKey, setMistralKey } from '@/lib/api'

interface SettingsModalProps {
  onClose: () => void
  onSave: () => void
}

export default function SettingsModal({ onClose, onSave }: SettingsModalProps) {
  const [key, setKey] = useState('')
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setKey(getMistralKey())
  }, [])

  const handleSave = () => {
    setMistralKey(key.trim())
    setSaved(true)
    setTimeout(() => {
      onSave()
      onClose()
    }, 800)
  }

  const handleRemove = () => {
    setMistralKey('')
    setKey('')
  }

  const steps = [
    { text: 'Acesse', link: { label: 'console.mistral.ai', href: 'https://console.mistral.ai' } },
    { text: 'Crie uma conta gratuita ou faça login' },
    { text: 'No menu lateral, clique em', link: { label: 'API Keys', href: 'https://console.mistral.ai/api-keys' } },
    { text: 'Clique em "Create new key", dê um nome e copie a chave gerada' },
  ]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(1,4,9,0.85)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="w-full max-w-lg card card-accent animate-fade-in"
        style={{ padding: '0' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                 style={{ background: 'rgba(163, 113, 247, 0.15)' }}>
              <Key className="w-4 h-4" style={{ color: 'var(--purple)' }} />
            </div>
            <div>
              <h2 className="font-semibold text-[15px]" style={{ color: 'var(--text)' }}>
                Configurar Mistral AI
              </h2>
              <p className="text-[11px]" style={{ color: 'var(--muted)' }}>
                Chave salva localmente no seu navegador
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5 border-0">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Steps */}
        <div className="p-5">
          <p className="text-[13px] font-medium mb-3" style={{ color: 'var(--muted)' }}>
            Como obter sua chave gratuita:
          </p>
          <div className="space-y-2.5 mb-5">
            {steps.map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-[11px] font-bold"
                     style={{ background: 'rgba(56,139,253,0.15)', color: 'var(--blue-light)' }}>
                  {i + 1}
                </div>
                <p className="text-[13px]" style={{ color: 'var(--muted)' }}>
                  {step.text}{' '}
                  {step.link && (
                    <a
                      href={step.link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 font-medium hover:underline"
                      style={{ color: 'var(--blue-light)' }}
                    >
                      {step.link.label}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </p>
              </div>
            ))}
          </div>

          {/* Key input */}
          <label className="text-[12px] font-semibold mb-1.5 block uppercase tracking-wide" style={{ color: 'var(--muted)' }}>
            Sua chave da API
          </label>
          <div className="relative">
            <input
              type={show ? 'text' : 'password'}
              value={key}
              onChange={(e) => { setKey(e.target.value); setSaved(false) }}
              placeholder="Cole sua chave aqui..."
              className="input-field pr-10"
            />
            <button
              type="button"
              onClick={() => setShow(!show)}
              className="absolute right-3 top-1/2 -translate-y-1/2"
              style={{ color: 'var(--muted)' }}
            >
              {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {key && (
            <button
              onClick={handleRemove}
              className="text-[12px] mt-2"
              style={{ color: 'var(--red)' }}
            >
              Remover chave
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-5 border-t gap-3" style={{ borderColor: 'var(--border)' }}>
          <button onClick={onClose} className="btn-ghost">
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={!key.trim() || saved}
            className="btn-primary"
            style={{ background: saved ? '#238636' : undefined }}
          >
            {saved ? (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Salvo!
              </>
            ) : (
              <>
                <ChevronRight className="w-4 h-4" />
                Salvar Chave
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
