import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { addFund, searchFunds } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import type { FundRead, FundSearchHit } from "@/shared/api/types";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";

import styles from "./FundSearchPicker.module.css";

const DEBOUNCE_MS = 380;

type FundSearchPickerProps = {
  inputId: string;
  disabled?: boolean;
  selectedFundId: number;
  /** Used to show label when каталог ещё не подтянулся или для свежих данных */
  selectedFund?: FundRead | null;
  onFundSelected: (fund: FundRead) => void;
  onClearFund: () => void;
  onAddError?: (title: string, message: string) => void;
};

export function FundSearchPicker({
  inputId,
  disabled,
  selectedFundId,
  selectedFund,
  onFundSelected,
  onClearFund,
  onAddError,
}: FundSearchPickerProps) {
  const qc = useQueryClient();
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(searchInput.trim()), DEBOUNCE_MS);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  useEffect(() => {
    if (selectedFundId > 0 && selectedFund) {
      setSearchInput(`${selectedFund.name} (${selectedFund.ticker})`);
    }
  }, [selectedFundId, selectedFund?.id, selectedFund?.name, selectedFund?.ticker]);

  const searchQ = useQuery({
    queryKey: queryKeys.fundsSearch(debouncedSearch),
    queryFn: () => searchFunds(debouncedSearch, 15),
    enabled: debouncedSearch.length >= 2,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!dropdownOpen) return;
    const onDoc = (e: MouseEvent) => {
      const el = wrapRef.current;
      if (!el || el.contains(e.target as Node)) return;
      setDropdownOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [dropdownOpen]);

  const addMutation = useMutation({
    mutationFn: addFund,
    onSuccess: async (fund) => {
      setDropdownOpen(false);
      setSearchInput(`${fund.name} (${fund.ticker})`);
      onFundSelected(fund);
      await qc.invalidateQueries({ queryKey: queryKeys.funds });
    },
    onError: (err: unknown) => {
      const e = getUserFacingApiError(err);
      onAddError?.(e.title, e.message);
    },
  });

  const busy = Boolean(disabled) || addMutation.isPending;
  const showDropdown = dropdownOpen && debouncedSearch.length >= 2;

  const onPick = (hit: FundSearchHit) => {
    addMutation.mutate({
      instrument_uid: hit.instrument_uid,
      ticker: hit.ticker,
      name: hit.name,
      figi: hit.figi,
      lot: hit.lot,
      currency: hit.currency,
    });
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.fieldWrap} ref={wrapRef}>
        <input
          id={inputId}
          className={styles.input}
          type="search"
          autoComplete="off"
          placeholder="Поиск по названию или тикеру (от 2 символов)"
          value={searchInput}
          disabled={busy}
          onFocus={() => setDropdownOpen(true)}
          onChange={(e) => {
            const v = e.target.value;
            setSearchInput(v);
            setDropdownOpen(true);
            if (selectedFundId > 0) {
              onClearFund();
            }
          }}
        />
        {showDropdown ? (
          <div className={styles.dropdown} role="listbox">
            {searchQ.isPending ? (
              <div className={styles.rowMuted}>Поиск…</div>
            ) : searchQ.isError ? (
              <div className={styles.rowMuted}>{getUserFacingApiError(searchQ.error).message}</div>
            ) : (searchQ.data?.length ?? 0) === 0 ? (
              <div className={styles.rowMuted}>Ничего не найдено</div>
            ) : (
              searchQ.data!.map((hit) => (
                <button
                  key={hit.instrument_uid}
                  type="button"
                  className={styles.item}
                  disabled={busy}
                  onClick={() => onPick(hit)}
                >
                  <span className={styles.title}>
                    {hit.name} <span className={styles.ticker}>{hit.ticker}</span>
                  </span>
                </button>
              ))
            )}
          </div>
        ) : null}
      </div>
      <p className={styles.hint}>T‑Invest (FindInstrument). Выбор строки добавляет инструмент в каталог и подставляет fund_id.</p>
    </div>
  );
}
