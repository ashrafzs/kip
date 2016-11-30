import React from 'react/addons';
import _ from 'underscore';

import bem from './bem';
import {t} from './utils';
import classNames from 'classnames';

var hotkey = require('react-hotkey');
hotkey.activate();

var ui = {};

ui.SmallInputBox = React.createClass({
  getValue () {
    return this.refs.inp.getDOMNode().value;
  },
  setValue (v) {
    this.refs.inp.getDOMNode().value = v;
  },
  render () {
    var elemId = _.uniqueId('elem');
    var value = this.props.value;
    var mdlKls = 'mdl-textfield mdl-js-textfield mdl-textfield--full-width';
    if (value) {
      mdlKls += ' is-dirty';
    }
    return (
        <div className={mdlKls}>
          <input type="text" ref='inp' className="mdl-textfield__input" value={value}
              onKeyUp={this.props.onKeyUp} onChange={this.props.onChange} id={elemId} />
          <label className="mdl-textfield__label" htmlFor={elemId} >{this.props.placeholder}</label>
        </div>
      );
  }
});

ui.SearchBox = React.createClass({
  getValue () {
    return this.refs.inp.getDOMNode().value;
  },
  setValue (v) {
    this.refs.inp.getDOMNode().value = v;
  },
  render () {
    var elemId = _.uniqueId('elem');
    var value = this.props.value;
    return (
        <input type="text" ref='inp' className="k-search__input" value={value}
            onKeyUp={this.props.onKeyUp} onChange={this.props.onChange} id={elemId} placeholder={this.props.placeholder}/>
      );
  }
});

ui.Panel = React.createClass({
  render () {
    return (
        <bem.uiPanel className={this.props.className} m={this.props.m}>
          <bem.uiPanel__body>
            {this.props.children}
          </bem.uiPanel__body>
        </bem.uiPanel>
      );
  }
});


ui.Modal = React.createClass({
  mixins: [hotkey.Mixin('handleHotkey')],
  handleHotkey: function(evt) {
    if (evt.keyCode === 27) {
      this.props.onClose.call(evt);
    }
  },
  backdropClick (evt) {
    if (evt.currentTarget === evt.target) {
      this.props.onClose.call(evt);
    }
  },
  renderTitle () {
    if (!this.props.title) {
      return null;
    } else if (this.props.small) {
      return (
          <div>
            <h4 className="modal-title">
              {this.props.title}
            </h4>
            <h6>
              {this.props.small}
            </h6>
          </div>
        );
    } else {
      return (
          <h4 className="modal-title">
            {this.props.title}
          </h4>
        );
    }
  },
  render () {
    return (
      // m={['done', isSearch ? 'search' : 'default']}
      <div className={classNames('modal-backdrop', this.props.className,
            this.props.large ? 'modal-large' : null,
            this.props.error ? 'modal-error' : null,
            this.props.title ? 'modal-titled' : null)}
          onClick={this.backdropClick}>
        <div className={classNames(this.props.open ? 'modal-open' : 'modal', this.props.icon ? 'modal--withicon' : null)}>
          {this.props.icon ?
            <i className={classNames('modal_icon', `modal_icon--${this.props.icon}`)} />
          :null}
          <div className={classNames('modal-content')}>
            <div className="modal-header">
              {this.renderTitle()}
              <a className="modal-x" type="button" onClick={this.props.onClose}>
                <i className="k-icon-close"></i>
              </a>
            </div>
            {this.props.children}
          </div>
        </div>
      </div>
    );
  }
});

ui.Modal.Footer = React.createClass({
  doneClick (evt) {
    alert('done!');
    this.props.onClose.call(evt);
  },
  render () {
    return <div className="modal-footer">{this.props.children}</div>;
  }
});

ui.Modal.Body = React.createClass({
  render () {
    return <div className="modal-body">{this.props.children}</div>;
  }
});


ui.Breadcrumb = React.createClass({
  render () {
    return (
        <ul className="ui-breadcrumb">
          {this.props.children}
        </ul>
      );
  }
});

ui.BreadcrumbItem = React.createClass({
  render () {
    return (
        <li className="ui-breadcrumb__item">
          {this.props.children}
        </li>
      );
  }
});


var SidebarAssetName = bem.create('sidebar-asset-name', '<span>');

ui.SidebarAssetName = React.createClass({
  render () {
    return (
        <SidebarAssetName m={{noname: !this.props.name}}>
          {this.props.name || t('No name')}
        </SidebarAssetName>
      );
  }
});

ui.AssetName = React.createClass({
  render () {
    var name = this.props.name,
        extra = false,
        isEmpty;
    var summary = this.props.summary;
    var row_count;
    if (!name) {
      row_count = summary.row_count;
      name = summary.labels ? summary.labels[0] : false;
      if (!name) {
        isEmpty = true;
        name = t('no name');
      }
      if (row_count) {
        if (row_count === 2) {
          extra = <small>{t('and one other question')}</small>;
        } else if (row_count > 2) {
          extra = <small>{t('and ## other questions').replace('##', row_count - 1)}</small>;
        }
      }
    }
    return (
        <span className={isEmpty ? 'asset-name asset-name--empty' : 'asset-name'}>
          {name}
          {extra ?
            extra
          : null }
        </span>
      );
  }
});

ui.MDLPopoverMenu = React.createClass({
  render () {
    var id = this.props.id;
    var button_tip = this.props.button_tip || t('More Actions');
    var button_type = this.props.button_type || 'icon';
    var caretClass = this.props.caretClass || 'fa fa-caret-down';
    var button_label = this.props.button_label;
    var classname = this.props.classname || 'ui-mdl-popover';
    var menuClasses = this.props.menuClasses || 'mdl-menu mdl-menu--bottom-right mdl-js-menu';
    return (
          <span className={classname}>
              { button_type == 'text' ?
                <button id={id} className="mdl-js-button">
                  {button_label}
                  <i className={caretClass} />
                </button>
              : button_type == 'cog-icon' ?
                <button id={id} className="mdl-js-button">
                  <i className="k-icon-settings-small" />
                </button>                
              :
                <button id={id} className="mdl-js-button" data-tip={button_tip}>
                  <i className="k-icon-more-actions" />
                </button>                
              }
            <div htmlFor={id} className={menuClasses}>
              {this.props.children}
            </div>
          </span>
    );
  }
});


export default ui;
