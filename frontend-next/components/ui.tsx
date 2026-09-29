"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { AlertCircle, ArrowDownLeft, ArrowUpRight, LoaderCircle, X } from "lucide-react";
import { number, type Quota } from "@/lib/api";

export function Brand() {
  return <div className="brand" aria-label="Getnet">getnet<span aria-hidden="true">.</span></div>;
}

export function Spinner() { return <LoaderCircle className="spin" size={18} aria-label="Carregando" />; }

export function ErrorNotice({ message }: { message: string }) {
  return message ? <div role="alert" className="notice error"><AlertCircle size={18} /><span>{message}</span></div> : null;
}

export function QuotaBars({ quota }: { quota: Quota }) {
  return <div className="quota-bars">{(["input", "output"] as const).map(kind => {
    const spent = quota[kind];
    const reserved = quota[`reservado_${kind}`];
    const limit = quota[`limite_${kind}`];
    const usedPercent = limit ? Math.min(100, spent / limit * 100) : 0;
    const reservedPercent = limit ? Math.min(100 - usedPercent, reserved / limit * 100) : 0;
    return <div key={kind} className={`quota-line ${kind}`}>
      <div className="row between"><span className="row">{kind === "input" ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}{kind === "input" ? "Entrada" : "Saída"}</span><strong>{limit ? `${Math.round((spent + reserved) / limit * 100)}%` : "Sem cota"}</strong></div>
      <div className="meter" role="meter" aria-label={`Cota de ${kind === "input" ? "entrada" : "saída"}`} aria-valuemin={0} aria-valuemax={Math.max(1, limit)} aria-valuenow={Math.min(spent + reserved, limit)}>
        <span style={{ width: `${usedPercent}%` }} /><span className="reserved" style={{ width: `${reservedPercent}%` }} />
      </div>
      <div className="row between small muted"><span><b>{number(spent)}</b> / {number(limit)}</span><span>tokens</span></div>
      {reserved > 0 && <div className="small muted reserved-note">{number(reserved)} reservados</div>}
    </div>;
  })}</div>;
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return <dialog ref={dialog} className="modal" onCancel={onClose} aria-labelledby="dialog-title">
    <div className="row between modal-heading"><h2 id="dialog-title">{title}</h2><button className="icon-button" title="Fechar" aria-label="Fechar" onClick={onClose}><X size={20} /></button></div>
    {children}
  </dialog>;
}